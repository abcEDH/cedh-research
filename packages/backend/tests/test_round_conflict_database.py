"""Opt-in, rollback-only PostgreSQL regression test for the Elo input guard.

Set RUN_ROUND_CONFLICT_DB_TESTS=1 and SUPABASE_DB_URL, then run with unittest.
Apply the round-conflict migration first. Never commits fixture rows.
"""

import os
import unittest
import uuid


@unittest.skipUnless(
    os.getenv("RUN_ROUND_CONFLICT_DB_TESTS") == "1", "requires explicit database-test opt-in"
)
class RoundConflictDatabaseTests(unittest.TestCase):
    def test_whole_pod_exclusion_and_league_exception(self):
        import psycopg2

        connection = psycopg2.connect(
            os.environ["SUPABASE_DB_URL"], port=5432, connect_timeout=15
        )
        try:
            with connection.cursor() as q:
                q.execute("SET statement_timeout='120s'")
                tid = str(uuid.uuid4())
                q.execute(
                    "INSERT INTO tournaments(id,topdeck_tid,name,start_date,"
                    "player_count,swiss_rounds,is_league) VALUES "
                    "(%s,%s,'Round integrity regression',now()-interval '1 day',8,2,false)",
                    (tid, "test-" + tid),
                )
                q.execute("SELECT id FROM commanders LIMIT 1")
                commander = q.fetchone()[0]
                entries = []
                for i in range(3):
                    pid, eid = str(uuid.uuid4()), str(uuid.uuid4())
                    q.execute(
                        "INSERT INTO players(id,topdeck_id,name) VALUES (%s,%s,%s)",
                        (pid, "test-" + pid, f"Test {i}"),
                    )
                    q.execute(
                        "INSERT INTO tournament_entries(id,tournament_id,player_id,commander_id) "
                        "VALUES (%s,%s,%s,%s)",
                        (eid, tid, pid, commander),
                    )
                    entries.append(eid)
                gids = [str(uuid.uuid4()), str(uuid.uuid4())]
                for i, gid in enumerate(gids):
                    q.execute(
                        "INSERT INTO games(id,tournament_id,round_number,table_number,"
                        "is_bracket,status,is_draw) VALUES (%s,%s,1,%s,false,'Completed',true)",
                        (gid, tid, i + 1),
                    )
                    for seat, eid in enumerate([entries[0], entries[i + 1]]):
                        q.execute(
                            "INSERT INTO game_participants(game_id,entry_id,seat_position,"
                            "result,points_earned) VALUES (%s,%s,%s,'draw',1)",
                            (gid, eid, seat),
                        )

                def eligible_count():
                    q.execute(
                        "SELECT count(*) FROM global_elo_game_results WHERE tournament_id=%s",
                        (tid,),
                    )
                    return q.fetchone()[0]

                self.assertEqual(
                    eligible_count(), 0, "exclude entire pods, including uninvolved opponents"
                )
                q.execute("UPDATE tournaments SET is_league=true WHERE id=%s", (tid,))
                self.assertEqual(eligible_count(), 4, "league rematches remain eligible")
                q.execute("UPDATE tournaments SET is_league=false WHERE id=%s", (tid,))
                q.execute("UPDATE games SET round_number=2 WHERE id=%s", (gids[1],))
                self.assertEqual(eligible_count(), 4, "different rounds are legitimate")
                q.execute(
                    "UPDATE games SET round_number=1,round_name='Round 1' WHERE id=%s",
                    (gids[1],),
                )
                self.assertEqual(
                    eligible_count(), 0, "round labels cannot bypass a numeric round collision"
                )
                q.execute("UPDATE games SET status='Active' WHERE id=%s", (gids[1],))
                self.assertEqual(
                    eligible_count(), 2, "inactive pairings do not suppress a completed pod"
                )
                q.execute(
                    "UPDATE tournaments SET start_date=now()+interval '1 day' WHERE id=%s",
                    (tid,),
                )
                self.assertEqual(eligible_count(), 0, "future-dated games never enter Elo")
        finally:
            connection.rollback()
            connection.close()
