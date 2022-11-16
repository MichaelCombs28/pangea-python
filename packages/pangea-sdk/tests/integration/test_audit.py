import os
import time
import unittest

import pangea.exceptions as pexc
from pangea import PangeaConfig
from pangea.response import PangeaResponse, ResponseStatus
from pangea.services import Audit
from pangea.services.audit.models import (
    EventSigning,
    EventVerification,
    LogOutput,
    SearchOrder,
    SearchOrderBy,
    SearchOutput,
)

ACTOR = "python-sdk"
MSG_NO_SIGNED = "test-message"
MSG_JSON = "JSON-message"
MSG_SIGNED_LOCAL = "sign-test-local"
STATUS_NO_SIGNED = "no-signed"
STATUS_SIGNED = "signed"


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.token = os.getenv("PANGEA_INTEGRATION_AUDIT_TOKEN")
        domain = os.getenv("PANGEA_INTEGRATION_DOMAIN")
        self.config = PangeaConfig(domain=domain)
        self.audit = Audit(self.token, config=self.config)
        self.auditSigner = Audit(
            self.token,
            config=self.config,
            private_key_file="./tests/testdata/privkey",
        )

    def test_log_no_verbose(self):
        response: PangeaResponse[LogOutput] = self.audit.log(
            message=MSG_NO_SIGNED, actor=ACTOR, status=STATUS_NO_SIGNED, verbose=False
        )
        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertIsNotNone(response.result.hash)
        self.assertIsNone(response.result.envelope)

    def test_log_verbose_no_verify(self):
        response: PangeaResponse[LogOutput] = self.audit.log(
            message=MSG_NO_SIGNED, actor=ACTOR, status=STATUS_NO_SIGNED, verify=False, verbose=True
        )
        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertIsNotNone(response.result.envelope)
        self.assertIsNone(response.result.consistency_proof)
        self.assertIsNotNone(response.result.membership_proof)
        self.assertEqual(response.result.consistency_verification, EventVerification.NONE)
        self.assertEqual(response.result.membership_verification, EventVerification.NONE)
        self.assertEqual(response.result.signature_verification, EventVerification.NONE)

    def test_log_verify(self):
        response: PangeaResponse[LogOutput] = self.audit.log(
            message=MSG_NO_SIGNED, actor=ACTOR, status=STATUS_NO_SIGNED, verify=True
        )  # Verify true set verbose to true
        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertIsNotNone(response.result.envelope)
        self.assertIsNone(response.result.consistency_proof)
        self.assertIsNotNone(response.result.membership_proof)
        self.assertEqual(
            response.result.consistency_verification, EventVerification.NONE
        )  # Cant verify consistency on first
        self.assertEqual(response.result.membership_verification, EventVerification.PASS)
        self.assertEqual(response.result.signature_verification, EventVerification.NONE)

        response: PangeaResponse[LogOutput] = self.audit.log(
            message=MSG_NO_SIGNED, actor=ACTOR, status=STATUS_NO_SIGNED, verify=True
        )
        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertIsNotNone(response.result.envelope)
        self.assertEqual(response.result.consistency_verification, EventVerification.PASS)  # but second should pass
        self.assertEqual(response.result.membership_verification, EventVerification.PASS)
        self.assertEqual(response.result.signature_verification, EventVerification.NONE)

    def test_log_json(self):
        new = {"customtag3": "mycustommsg3", "ct4": "cm4"}
        old = {"customtag5": "mycustommsg5", "ct6": "cm6"}

        response = self.audit.log(
            message=MSG_JSON,
            actor=ACTOR,
            action="Action",
            source="Source",
            status=STATUS_NO_SIGNED,
            target="Target",
            new=new,
            old=old,
            verify=True,
        )

        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertIsNotNone(response.result.envelope)
        self.assertIsInstance(response.result.envelope.event.new, dict)
        self.assertIsInstance(response.result.envelope.event.old, dict)
        self.assertIsNotNone(response.result.envelope)
        self.assertIsNotNone(response.result.membership_proof)
        self.assertEqual(response.result.membership_verification, EventVerification.PASS)
        self.assertEqual(response.result.signature_verification, EventVerification.NONE)

    def test_log_sign_local_and_verify(self):
        response = self.auditSigner.log(
            message=MSG_SIGNED_LOCAL,
            actor=ACTOR,
            action="Action",
            source="Source",
            status=STATUS_SIGNED,
            target="Target",
            new="New",
            old="Old",
            signing=EventSigning.LOCAL,
            verify=True,
        )
        self.assertEqual(response.status, ResponseStatus.SUCCESS)

        self.assertIsNotNone(response.result.envelope)
        self.assertIsNone(response.result.consistency_proof)
        self.assertIsNotNone(response.result.membership_proof)
        self.assertEqual(response.result.consistency_verification, EventVerification.NONE)
        self.assertEqual(response.result.membership_verification, EventVerification.PASS)
        self.assertEqual(response.result.signature_verification, EventVerification.PASS)
        self.assertEqual(response.result.envelope.public_key, "lvOyDMpK2DQ16NI8G41yINl01wMHzINBahtDPoh4+mE=")

    def test_log_json_sign_local_and_verify(self):
        new = {"customtag3": "mycustommsg3", "ct4": "cm4"}
        old = {"customtag5": "mycustommsg5", "ct6": "cm6"}

        response = self.auditSigner.log(
            message=MSG_JSON,
            actor=ACTOR,
            action="Action",
            source="Source",
            status=STATUS_NO_SIGNED,
            target="Target",
            new=new,
            old=old,
            signing=EventSigning.LOCAL,
            verify=True,
        )

        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertIsNotNone(response.result.envelope)
        self.assertIsInstance(response.result.envelope.event.new, dict)
        self.assertIsInstance(response.result.envelope.event.old, dict)
        self.assertIsNotNone(response.result.envelope)
        self.assertIsNone(response.result.consistency_proof)
        self.assertIsNotNone(response.result.membership_proof)
        self.assertEqual(response.result.membership_verification, EventVerification.PASS)
        self.assertEqual(response.result.signature_verification, EventVerification.PASS)

    def test_search_results_verbose(self):
        limit = 2
        max_result = 2
        response_search = self.audit.search(
            query="message:" + MSG_SIGNED_LOCAL,
            order=SearchOrder.ASC,
            limit=limit,
            max_results=max_result,
            verbose=True,
        )
        self.assertEqual(response_search.status, ResponseStatus.SUCCESS)
        self.assertEqual(len(response_search.result.events), limit)
        self.assertEqual(response_search.result.count, max_result)

        resultsLimit = 2
        # Verify consistency en true
        response_results = self.audit.results(id=response_search.result.id, limit=resultsLimit, verify_consistency=True)
        self.assertEqual(response_results.status, ResponseStatus.SUCCESS)
        self.assertEqual(len(response_results.result.events), resultsLimit)
        for event in response_results.result.events:
            self.assertEqual(event.consistency_verification, EventVerification.PASS)
            self.assertEqual(event.membership_verification, EventVerification.PASS)

        # Verify consistency en false
        response_results = self.audit.results(
            id=response_search.result.id, limit=resultsLimit, offset=1, verify_consistency=False
        )
        self.assertEqual(response_results.status, ResponseStatus.SUCCESS)
        self.assertEqual(len(response_results.result.events), resultsLimit)
        for event in response_results.result.events:
            self.assertEqual(event.consistency_verification, EventVerification.NONE)
            self.assertEqual(event.membership_verification, EventVerification.NONE)

        try:
            # This should fail because offset is out of range
            response_results = self.audit.results(id=response_search.result.id, limit=1, offset=max_result + 1)
            self.assertEqual(len(response_results.result.events), 0)
        except Exception as e:
            # FIXME: Remove and fix once endpoint is fixed. Have to return error
            self.assertTrue(False)
            self.assertTrue(isinstance(e, pexc.PangeaAPIException))
            print(e)

    def test_search_results_no_verbose(self):
        limit = 10
        max_result = 10
        response_search = self.audit.search(query="message:", limit=limit, max_results=max_result, verbose=False)
        self.assertEqual(response_search.status, ResponseStatus.SUCCESS)
        self.assertEqual(len(response_search.result.events), limit)
        self.assertEqual(response_search.result.count, max_result)

        resultsLimit = 2
        # Verify consistency en true
        response_results = self.audit.results(id=response_search.result.id, limit=resultsLimit, verify_consistency=True)
        self.assertEqual(response_results.status, ResponseStatus.SUCCESS)
        self.assertEqual(len(response_results.result.events), resultsLimit)
        for event in response_results.result.events:
            self.assertEqual(event.consistency_verification, EventVerification.NONE)
            self.assertEqual(event.membership_verification, EventVerification.NONE)

        # Verify consistency en false
        response_results = self.audit.results(
            id=response_search.result.id, limit=resultsLimit, offset=1, verify_consistency=False
        )
        self.assertEqual(response_results.status, ResponseStatus.SUCCESS)
        self.assertEqual(len(response_results.result.events), resultsLimit)
        for event in response_results.result.events:
            self.assertEqual(event.consistency_verification, EventVerification.NONE)
            self.assertEqual(event.membership_verification, EventVerification.NONE)

        try:
            # This should fail because offset is out of range
            response_results = self.audit.results(id=response_search.result.id, limit=1, offset=max_result + 1)
            self.assertEqual(len(response_results.result.events), 0)
        except Exception as e:
            # FIXME: Remove and fix once endpoint is fixed. Have to return error
            self.assertTrue(False)
            self.assertTrue(isinstance(e, pexc.PangeaAPIException))
            print(e)

    def test_root_1(self):
        response = self.audit.root()
        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertTrue(isinstance(response.result.data.tree_name, str))
        self.assertNotEqual(response.result.data.tree_name, "")
        self.assertTrue(isinstance(response.result.data.root_hash, str))
        self.assertNotEqual(response.result.data.root_hash, "")
        self.assertTrue(isinstance(response.result.data.size, int))
        self.assertTrue(isinstance(response.result.data.url, str))
        self.assertNotEqual(response.result.data.url, "")
        self.assertGreaterEqual(len(response.result.data.consistency_proof), 1)

    def test_root_2(self):
        tree_size = 3
        response = self.audit.root(tree_size=tree_size)
        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        self.assertEqual(response.result.data.size, tree_size)

        self.assertTrue(isinstance(response.result.data.tree_name, str))
        self.assertNotEqual(response.result.data.tree_name, "")
        self.assertTrue(isinstance(response.result.data.root_hash, str))
        self.assertNotEqual(response.result.data.root_hash, "")
        self.assertTrue(isinstance(response.result.data.url, str))
        self.assertNotEqual(response.result.data.url, "")
        self.assertGreaterEqual(len(response.result.data.consistency_proof), 1)

    def test_search_verify(self):
        query = "message:sigtest100"
        response = self.audit.search(
            query=query,
            order=SearchOrder.DESC,
            limit=2,
            max_results=2,
            verify_consistency=True,
            verify_events=True,
            start="7d",
        )

        self.assertEqual(response.status, ResponseStatus.SUCCESS)
        print("events: ", len(response.result.events))
        for idx, search_event in enumerate(response.result.events):
            self.assertEqual(search_event.consistency_verification, EventVerification.PASS)
            self.assertEqual(search_event.membership_verification, EventVerification.PASS)

    def test_search_sort(self):
        timestamp = time.time()
        msg = f"test-{timestamp}"
        authors = ["alex", "bob", "chris", "david", "evan"]

        for idx in range(0, len(authors)):
            resp = self.audit.log(message=msg, actor=authors[idx])
            self.assertEqual(resp.status, ResponseStatus.SUCCESS)

        query = "message:" + msg
        r_desc: PangeaResponse[SearchOutput] = self.audit.search(
            query=query, order=SearchOrder.DESC, order_by=SearchOrderBy.RECEIVED_AT, limit=len(authors)
        )
        self.assertEqual(r_desc.status, ResponseStatus.SUCCESS)
        self.assertEqual(len(r_desc.result.events), len(authors))

        for idx in range(0, len(authors)):
            self.assertEqual(r_desc.result.events[idx].envelope.event.actor, authors[idx])

        r_asc = self.audit.search(
            query=query, order=SearchOrder.ASC, order_by=SearchOrderBy.RECEIVED_AT, limit=len(authors)
        )
        self.assertEqual(r_asc.status, ResponseStatus.SUCCESS)
        self.assertEqual(len(r_asc.result.events), len(authors))

        for idx in range(0, len(authors)):
            self.assertEqual(r_asc.result.events[len(authors) - 1 - idx].envelope.event.actor, authors[idx])


if __name__ == "__main__":
    unittest.main()
