import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.hand_eval import evaluate_hand, keep_or_mull


def card(name, type_line, mana_cost=None, oracle_text=None):
    return {
        'name': name,
        'type_line': type_line,
        'mana_cost': mana_cost or '',
        'oracle_text': oracle_text or ''
    }


class HandEvalTests(unittest.TestCase):
    def setUp(self):
        self.kinnan_labels = {
            'commander_names': ['Kinnan, Bonder Prodigy'],
            'commander_cost': 'GU',
            'commander_colors': ['G', 'U'],
            'ramp_rocks': [],
            'engines': [],
            'tutors': [],
            'wins': []
        }
        self.cache = {}

    def test_dork_carry(self):
        hand = [
            card('Forest', 'Basic Land — Forest', oracle_text='Add {G}.'),
            card('Llanowar Elves', 'Creature — Elf Druid', mana_cost='{G}', oracle_text='{T}: Add {G}.'),
        ]
        evals = evaluate_hand(hand, self.kinnan_labels, self.cache, seat=2)
        self.assertGreaterEqual(evals['t2_total'], 2)

    def test_birds_color_fix(self):
        hand = [
            card('Forest', 'Basic Land — Forest', oracle_text='Add {G}.'),
            card('Birds of Paradise', 'Creature — Bird', mana_cost='{G}', oracle_text='{T}: Add one mana of any color.'),
        ]
        evals = evaluate_hand(hand, self.kinnan_labels, self.cache, seat=2)
        self.assertIn('U', evals['colors'])

    def test_kinnan_early7_keep(self):
        hand_eval = {
            'castable_t1': [],
            'castable_t2': [],
            'castable_t3': [],
            'commander_turn': 'T2',
            't1_total': 7,
            't2_total': 7,
        }
        decision, reason = keep_or_mull(hand_eval, 'mixed', 2, self.kinnan_labels)
        self.assertEqual(decision, 'keep')
        self.assertIn('early 7-mana', reason)


if __name__ == '__main__':
    unittest.main()
