from wellnessbox_rnd.domain.loaders import load_safety_rules
from wellnessbox_rnd.domain.models import SafetyRuleSet


def get_safety_rule_set() -> SafetyRuleSet:
    return load_safety_rules()

