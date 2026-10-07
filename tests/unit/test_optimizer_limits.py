"""The deletion cap: which of the three ceilings wins.

`effective_max_deletions` is the one place that decides how many entities an
optimization run may remove. Three numbers want to be in charge -- the strategy
preset, the operator's COGNITIVE_FABRIC_OPTIMIZER_MAX_DELETIONS, and the
caller's own `maxDeletions` -- and the rule is that the lowest of them wins.
These tests pin that rule, because each of the interesting mistakes is a
different one of the three winning: the caller lifting the operator's cap, the
operator's cap overriding a conservative strategy, or an absent request meaning
"unlimited" as it used to.
"""

import pytest

from cognitive_fabric.agents.memory_optimizer.context_builder import (
    DEFAULT_STRATEGY,
    STRATEGY_CONFIGS,
    effective_max_deletions,
)


class TestStrategyPresets:
    def test_each_strategy_has_a_limit(self):
        for name, config in STRATEGY_CONFIGS.items():
            assert isinstance(config["max_deletions"], int), name
            assert config["max_deletions"] > 0, name

    def test_the_limits_are_ordered_from_careful_to_bold(self):
        """A strategy named `aggressive` must not delete less than `conservative`."""
        limits = {
            name: config["max_deletions"] for name, config in STRATEGY_CONFIGS.items()
        }
        assert limits["conservative"] < limits["balanced"] < limits["aggressive"]

    def test_an_unknown_strategy_does_not_get_the_boldest_preset(self):
        """A hallucinated strategy name must not be the one that deletes most.

        The limit that applies to an unrecognised name is the default's, and the
        default is not `aggressive`.
        """
        assert DEFAULT_STRATEGY != "aggressive"
        assert effective_max_deletions("no-such-strategy") == (
            STRATEGY_CONFIGS[DEFAULT_STRATEGY]["max_deletions"]
        )


class TestTheLowestCeilingWins:
    def test_nothing_configured_means_the_strategy_limit(self):
        for name, config in STRATEGY_CONFIGS.items():
            assert effective_max_deletions(name) == config["max_deletions"], name

    def test_the_operator_cap_lowers_the_strategy_limit(self):
        assert effective_max_deletions("aggressive", operator_cap=30) == 30

    def test_the_operator_cap_cannot_raise_the_strategy_limit(self):
        """Raising the cap above the strategy's own limit is not a thing it does.

        A cap of 1000 on `conservative` is still 10 deletions: the strategy is a
        ceiling too, and an operator who wants more picks a bolder strategy
        rather than a larger number.
        """
        assert effective_max_deletions("conservative", operator_cap=1000) == 10

    def test_the_caller_cannot_raise_the_operator_cap(self):
        """`maxDeletions` comes from the model, so it can only lower the cap."""
        asked, cap = 500, 30
        assert effective_max_deletions("aggressive", asked, cap) == 30

    def test_the_caller_can_lower_the_operator_cap(self):
        assert effective_max_deletions("aggressive", requested=5, operator_cap=30) == 5

    def test_the_caller_cannot_raise_the_strategy_limit_alone(self):
        assert effective_max_deletions("conservative", requested=1000) == 10

    def test_a_cap_of_zero_deletes_nothing(self):
        """Zero is a value, not an absent setting. It must survive the min()."""
        assert effective_max_deletions("aggressive", operator_cap=0) == 0
        assert effective_max_deletions("aggressive", requested=0) == 0


class TestAgainstConfiguration:
    def test_the_setting_defaults_to_unset(self):
        """Unset, not zero and not a number: the strategy's limit is the limit.

        A default of 0 would delete nothing; a default of 50 would silently
        lower `aggressive` for everyone who never configured it.
        """
        from cognitive_fabric.config import Settings

        assert Settings().optimizer_max_deletions is None

    def test_the_setting_reads_the_documented_name(self, monkeypatch):
        from cognitive_fabric.config import Settings

        monkeypatch.setenv("COGNITIVE_FABRIC_OPTIMIZER_MAX_DELETIONS", "7")
        assert Settings().optimizer_max_deletions == 7

    def test_a_negative_cap_is_refused(self, monkeypatch):
        from pydantic import ValidationError

        from cognitive_fabric.config import Settings

        monkeypatch.setenv("COGNITIVE_FABRIC_OPTIMIZER_MAX_DELETIONS", "-1")
        with pytest.raises(ValidationError):
            Settings()


class TestThePlanLimitCapsOnlyDeletions:
    """The planner's half of the cap, applied before anything is executed.

    `_apply_strategy_limits` used to truncate the whole action list, so a plan
    of many updates and a few deletions came back as a prefix of itself -- the
    deletions gone and work the limit was never about thrown away with them.
    """

    @staticmethod
    def _apply(actions, strategy):
        from cognitive_fabric.agents.memory_optimizer.services.planning import (
            OptimizationPlanService,
        )

        # The method reads no instance state: the strategy and the operator's
        # cap are its whole input.
        return OptimizationPlanService._apply_strategy_limits(None, actions, strategy)

    @staticmethod
    def _action(i, action_type, risk="low"):
        from cognitive_fabric.types.optimization import AgentOptimizationAction

        return AgentOptimizationAction(
            action_type=action_type,
            entity_type="component",
            entity_id=f"e-{i}",
            entity_name=f"E{i}",
            reason="test",
            risk_level=risk,
        )

    def test_updates_are_never_trimmed(self):
        actions = [self._action(i, "update") for i in range(30)]
        actions += [self._action(f"d{i}", "delete") for i in range(3)]
        kept = self._apply(actions, "conservative")
        assert len(kept) == 33
        assert sum(1 for a in kept if a.action_type == "delete") == 3
        assert sum(1 for a in kept if a.action_type == "update") == 30

    def test_deletions_beyond_the_limit_are_dropped(self):
        actions = [self._action(f"d{i}", "delete") for i in range(15)]
        kept = self._apply(actions, "conservative")
        assert len(kept) == 10

    def test_the_operator_cap_reaches_the_planner_too(self, monkeypatch):
        """A plan must not promise deletions the executor would refuse."""
        from cognitive_fabric.config import settings as cf_settings

        monkeypatch.setattr(cf_settings, "optimizer_max_deletions", 2)
        actions = [self._action(f"d{i}", "delete") for i in range(15)]
        kept = self._apply(actions, "aggressive")
        assert len(kept) == 2


class TestTheDefaultStrategyHasOneHome:
    """Every entry point resolves the default from `Settings`, not a literal.

    Three user-facing paths used to spell `"balanced"` themselves -- the MCP
    schema, `agent.run`, and the plan prompt -- so
    `COGNITIVE_FABRIC_OPTIMIZER_DEFAULT_STRATEGY` changed nothing any of them
    did. The configured default is `conservative`; a path that quietly says
    `balanced` deletes five times as many entities as the operator asked for.
    """

    def _strategy_run_passes_to_optimize(self, **kwargs):
        import asyncio
        from unittest.mock import MagicMock

        from cognitive_fabric.agents.memory_optimizer.agent import (
            MemoryOptimizationAgent,
        )

        agent = MemoryOptimizationAgent(MagicMock())
        seen = {}

        async def capture(**call_kwargs):
            seen.update(call_kwargs)
            return {}

        agent.optimize = capture
        asyncio.run(agent.run(repository="r", branch="main", **kwargs))
        return seen

    def test_an_unspecified_strategy_resolves_to_the_configured_one(self, monkeypatch):
        from cognitive_fabric.config import settings as cf_settings
        from cognitive_fabric.types.optimization import OptimizationStrategy

        monkeypatch.setattr(cf_settings, "optimizer_default_strategy", "aggressive")
        passed = self._strategy_run_passes_to_optimize()
        assert passed["strategy"] == OptimizationStrategy.AGGRESSIVE

    def test_an_explicit_strategy_still_wins(self):
        from cognitive_fabric.types.optimization import OptimizationStrategy

        passed = self._strategy_run_passes_to_optimize(strategy="aggressive")
        assert passed["strategy"] is OptimizationStrategy.AGGRESSIVE

    def test_an_unrecognised_strategy_is_refused_not_defaulted(self):
        # `run` turns an unrecognised name into a ValueError rather than
        # falling back to the configured default. This deletes memory, so a
        # mistyped name must not quietly become a strategy the operator did
        # not choose -- and it must not quietly become *no* strategy either.
        with pytest.raises(ValueError):
            self._strategy_run_passes_to_optimize(strategy="louvain-typo")

    def test_the_plan_prompt_names_a_missing_strategy_instead_of_inventing_one(self):
        from cognitive_fabric.agents.memory_optimizer.prompt_manager import (
            PromptManager,
        )

        with pytest.raises(KeyError):
            PromptManager().build_optimization_prompt({})
