"""Guard parser/interpreter assumptions independently of diplomacy scripts."""
import unittest

from tools.validate_diplomacy import Runtime, ScriptError, expand, parse


class ParserTests(unittest.TestCase):
    def test_comments_quoted_hash_bom_duplicate_fields_and_comparators(self):
        nodes = parse('\ufeffsample = { # comment\n name = "x # y" trust > -20 trust <= 100 target = URS target = COL }')
        sample = nodes[0]
        self.assertEqual(sample.scalar("name"), "x # y")
        self.assertEqual([(n.op, n.value) for n in sample.fields("trust")], [(">", "-20"), ("<=", "100")])
        self.assertEqual(len(sample.fields("target")), 2)

    def test_rejects_unbalanced_input(self):
        for source in ("x = {", "x = yes }", "x =", "x = { y = }"):
            with self.subTest(source=source), self.assertRaises(ScriptError):
                parse(source)

    def test_anonymous_target_list(self):
        node = parse("targets = { URS COL SAR }")[0]
        self.assertEqual([child.key for child in node.children], ["URS", "COL", "SAR"])

    def test_macro_expands_keys_and_values_without_altering_definition(self):
        original = parse("effect = { set_variable = { trust_$TARGET$ = $TRUST$ } $PARTNER$ = { x = 1 } }")[0]
        expanded = expand(original, {"TARGET": "SAR", "TRUST": "12", "PARTNER": "FROM"})
        self.assertEqual(expanded.children[0].children[0].key, "trust_SAR")
        self.assertEqual(expanded.children[0].children[0].value, "12")
        self.assertEqual(expanded.children[1].key, "FROM")
        self.assertIn("$TARGET$", original.children[0].children[0].key)

    def test_native_variable_default_comparison_and_explicit_equals(self):
        runtime = Runtime()
        scope = runtime.scope("SGN")
        runtime.country("SGN").variables["sample"] = 51
        self.assertTrue(runtime.check(parse("check_variable = { sample = 50 }"), scope))
        self.assertTrue(runtime.check(parse("check_variable = { var = sample value = 50 }"), scope))
        self.assertFalse(runtime.check(parse("check_variable = { sample = 50 compare = equals }"), scope))
        self.assertFalse(runtime.check(parse("check_variable = { var = sample value = 50 compare = equals }"), scope))

    def test_unknown_evaluated_primitive_is_rejected(self):
        runtime = Runtime()
        scope = runtime.scope("SGN")
        with self.assertRaises(ScriptError):
            runtime.check(parse("invented_trigger = yes"), scope)
        with self.assertRaises(ScriptError):
            runtime.execute(parse("invented_effect = yes"), scope)


if __name__ == "__main__":
    unittest.main()
