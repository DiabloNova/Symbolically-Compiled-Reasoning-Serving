import hashlib, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts/data"))
from verify_public_evidence_snapshot import VerificationError, safe_path, verify_split

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.info={"status":"approved","redistribution_allowed_with_attribution":True,"license_spdx":"CC-BY-4.0","task_license":"CC BY 4.0","license_url":"https://creativecommons.org/licenses/by/4.0/","task_page":"https://example.org/task","attribution":"Attributed task","labels":["Yes","No"]}
        self.rev="a"*40
        self.raw=b"index\ttext\tanswer\n0\tA deadline is 30 days.\tYes\n1\tNo deadline applies.\tNo\n"
        rows=[{"index":0,"task":"sample","split":"test","fields":{"index":0,"text":"A deadline is 30 days.","answer":"Yes"}},{"index":1,"task":"sample","split":"test","fields":{"index":1,"text":"No deadline applies.","answer":"No"}}]
        self.jsonl=("".join(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n" for r in rows)).encode()
        self.side={"task":"sample","split":"test","upstream_revision":self.rev,"upstream_source_url":"https://example.org/resolve/"+self.rev+"/test.tsv","task_license":"CC BY 4.0","task_license_spdx":"CC-BY-4.0","task_license_url":"https://creativecommons.org/licenses/by/4.0/","official_task_page":"https://example.org/task","attribution":"Attributed task","allowed_labels":["Yes","No"],"columns":["index","text","answer"],"raw_sha256":hashlib.sha256(self.raw).hexdigest(),"raw_bytes":len(self.raw),"normalized_jsonl_sha256":hashlib.sha256(self.jsonl).hexdigest(),"normalized_jsonl_bytes":len(self.jsonl),"rows_written":2}
    def verify(self,raw=None,jsonl=None,side=None,info=None):
        return verify_split("sample","test",self.raw if raw is None else raw,self.jsonl if jsonl is None else jsonl,json.dumps(self.side if side is None else side).encode(),self.info if info is None else info,self.rev)
    def test_valid_payload(self):
        self.assertEqual(self.verify()["rows"],2)
    def test_raw_hash_tampering_rejected(self):
        with self.assertRaises(VerificationError): self.verify(raw=self.raw+b"changed")
    def test_jsonl_field_tampering_rejected_even_with_updated_hash(self):
        val=self.jsonl.replace(b"30 days",b"90 days"); meta=dict(self.side); meta["normalized_jsonl_sha256"]=hashlib.sha256(val).hexdigest(); meta["normalized_jsonl_bytes"]=len(val)
        with self.assertRaises(VerificationError): self.verify(jsonl=val,side=meta)
    def test_unapproved_licence_rejected(self):
        info=dict(self.info); info["redistribution_allowed_with_attribution"]=False
        with self.assertRaises(VerificationError): self.verify(info=info)
    def test_unknown_label_rejected(self):
        val=self.jsonl.replace(b'"answer":"Yes"',b'"answer":"Maybe"'); meta=dict(self.side); meta["normalized_jsonl_sha256"]=hashlib.sha256(val).hexdigest(); meta["normalized_jsonl_bytes"]=len(val)
        with self.assertRaises(VerificationError): self.verify(jsonl=val,side=meta)
    def test_archive_path_must_be_relative_and_normalized(self):
        with self.assertRaises(VerificationError): safe_path("/root/file")
        bad="x/"+chr(46)+chr(46)+"/y"
        with self.assertRaises(VerificationError): safe_path(bad)
        self.assertEqual(str(safe_path("data/public/legalbench/task/test.tsv")),"data/public/legalbench/task/test.tsv")

if __name__=="__main__": unittest.main()
