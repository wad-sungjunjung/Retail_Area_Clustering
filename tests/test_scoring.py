from src.scoring import GENERAL_CODE, HybridClassifier, MlClusterer, RuleScorer


def test_scoring_classes_instantiable():
    assert RuleScorer(weights={})
    assert MlClusterer()
    assert HybridClassifier()
    assert GENERAL_CODE == "GENERAL"
