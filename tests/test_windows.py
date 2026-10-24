"""Small fixtures test observation boundaries independently of the real dataset."""
import unittest
from pathlib import Path
import duckdb
import pandas as pd

SQL=(Path(__file__).resolve().parents[1]/'sql/01_pipeline.sql').read_text(encoding='utf-8')

def fixtures():
    users=pd.DataFrame([dict(user_id=i,install_date='1/1/2024',active_at=a,expire_date='1/1/2025',os='ios',age='adult',motivation='Other',plan='Full') for i,a in [(1,'1/1/2024'),(2,'1/2/2024'),(3,'1/1/2024')]])
    logs=[]
    for uid,date,h in [(1,'1/1/2024',10),(1,'1/2/2024',10),(1,'1/30/2024',0)]:
        dt=pd.Timestamp(date)
        logs.append(dict(user_id=uid,check_in_date=date,total_using_time=h,gym=0,other=h,communicate_roadmap=0,vocabulary_roadmap=0,onion_gpt=0,total_complete_lesson=0,check_in_day=dt.day,check_in_month=dt.month,check_in_year=dt.year))
    return users,pd.DataFrame(logs)

def build(u,l):
    c=duckdb.connect(); c.register('raw_users',u); c.register('raw_learning',l); c.execute(SQL); return c

class Windows(unittest.TestCase):
    def test_complete_boundary_and_zero_activity(self):
        c=build(*fixtures())
        rows=c.execute('SELECT user_id,study_hours,goal_user,longest_study_streak FROM user_windows WHERE period_days=30 ORDER BY user_id').fetchall()
        self.assertEqual(rows,[(1,20.0,True,2),(3,0.0,False,0)])
        # User 2 has only 29 observable days and must not count as a failure.
        self.assertEqual(c.execute('SELECT count(*) FROM user_windows WHERE user_id=2').fetchone()[0],0)
        self.assertEqual(c.execute("SELECT module_days,repeat_user FROM module_user30 WHERE user_id=1 AND module='other'").fetchone(),(2,True))
        self.assertEqual(c.execute('SELECT study_days,checkin_days FROM user_weeks WHERE user_id=1 AND week_index=4').fetchall(),[])
        c.close()

    def test_duplicates_rejected(self):
        u,l=fixtures()
        with self.assertRaises(duckdb.Error): build(u,pd.concat([l,l.iloc[[0]]]))

    def test_missing_and_negative_not_zero_filled(self):
        for value in [None,-1]:
            u,l=fixtures(); l.loc[0,'other']=value
            with self.assertRaises(duckdb.Error): build(u,l)

    def test_unknown_user_rejected(self):
        u,l=fixtures(); l.loc[0,'user_id']=999
        with self.assertRaises(duckdb.Error): build(u,l)

if __name__=='__main__': unittest.main()
