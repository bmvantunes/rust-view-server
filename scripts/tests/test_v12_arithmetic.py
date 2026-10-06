import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('measurement_v12',Path(__file__).parents[1]/'measurement_v12.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Arithmetic(unittest.TestCase):
 def test_portable_integer_fixture(self):
  a=[1,32,256];n=[1,9007199254740993,123456789]
  self.assertEqual(m.rate(a,n),{'count':289,'nanoseconds':9007199378197783,'per_second':'0.000032'})
  self.assertEqual(m.rate([1,1,1],[1,1,1])['per_second'],'1000000000.000000')
 def test_material_tampering_and_exact_timing(self):
  original=m.rate([1,32],[100,3200]);self.assertNotEqual(original,m.rate([1,31],[100,3200]))
  self.assertNotEqual(original,m.rate([1,32],[101,3200]))
  for counts,times in [([1],[0]),([1.0],[1]),([1],[-1]),([] ,[])]:
   with self.assertRaises(ValueError):m.rate(counts,times)
