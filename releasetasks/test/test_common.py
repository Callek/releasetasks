import unittest

from jose import jwt, jws
from jose.constants import ALGORITHMS

from releasetasks import sign_task
from releasetasks.test import PVT_KEY, PUB_KEY, OTHER_PUB_KEY, make_task_graph, \
    PVT_KEY_FILE, do_common_assertions, get_task_by_name


class TestTaskSigning(unittest.TestCase):

    def test_task_id(self):
        token = sign_task("xyz", pvt_key=PVT_KEY)
        claims = jwt.decode(token, PUB_KEY, algorithms=[ALGORITHMS.RS512])
        assert claims["taskId"] == "xyz"

    def test_exp(self):
        token = sign_task("xyz", pvt_key=PVT_KEY)
        claims = jwt.decode(token, PUB_KEY, algorithms=[ALGORITHMS.RS512])
        assert "exp" in claims

    def test_exp_int(self):
        token = sign_task("xyz", pvt_key=PVT_KEY)
        claims = jwt.decode(token, PUB_KEY, algorithms=[ALGORITHMS.RS512])
        assert isinstance(claims["exp"], int)

    def test_verify(self):
        token = sign_task("xyz", pvt_key=PVT_KEY)
        claims = jws.verify(token, PUB_KEY, algorithms=[ALGORITHMS.RS512])
        assert claims["taskId"] == "xyz"

    def test_verify_bad_signature(self):
        token = sign_task("xyz", pvt_key=PVT_KEY)
        self.assertRaises(jws.JWSError, jws.verify, token, OTHER_PUB_KEY,
                          [ALGORITHMS.RS512])


class TestEncryption(unittest.TestCase):
    maxDiff = 30000

    def test_encryption(self):
        graph = make_task_graph(
            version="42.0b2",
            next_version="42.0b3",
            appVersion="42.0",
            buildNumber=3,
            source_enabled=False,
            updates_enabled=True,
            bouncer_enabled=False,
            push_to_candidates_enabled=False,
            postrelease_version_bump_enabled=False,
            en_US_config={"platforms": {
                "macosx64": {"task_id": "xyz"},
                "win32": {"task_id": "xyy"}
            }},
            l10n_config={},
            partial_updates={
                "38.0": {
                    "buildNumber": 1,
                },
                "37.0": {
                    "buildNumber": 2,
                },
            },
            branch="mozilla-beta",
            product="firefox",
            revision="abcdef123456",
            balrog_api_root="https://fake.balrog/api",
            signing_class="dep-signing",
            release_channels=["beta"],
            signing_pvt_key=PVT_KEY_FILE,
            repo_path="foo/bar",
        )
        do_common_assertions(graph)
        for p in ("win32", "macosx64"):
            for v in ("38.0build1", "37.0build2"):
                balrog = get_task_by_name(graph, "{}_en-US_{}_funsize_balrog_task".format(p, v))
                self.assertEqual(len(balrog["task"]["payload"]["encryptedEnv"]), 2)
                self.assertTrue(
                    balrog["task"]["payload"]["encryptedEnv"][0].startswith("wcB"),
                    "Encrypted string should always start with 'wcB'")


class TestGraphScopes(unittest.TestCase):
    maxDiff = 30000
    graph = None

    def setUp(self):
        self.graph = make_task_graph(
            version="42.0b2",
            next_version="42.0b3",
            appVersion="42.0",
            buildNumber=3,
            branch="foo",
            revision="abcdef123456",
            updates_enabled=False,
            bouncer_enabled=False,
            source_enabled=False,
            push_to_candidates_enabled=False,
            postrelease_version_bump_enabled=False,
            en_US_config={"platforms": {
                "linux": {"task_id": "xyz"},
                "win32": {"task_id": "xyy"}
            }},
            l10n_config={},
            verifyConfigs={},
            signing_pvt_key=PVT_KEY_FILE,
        )

    def test_common_assertions(self):
        do_common_assertions(self.graph)

    def test_no_tasks(self):
        self.assertIsNone(self.graph["tasks"])

    def test_scopes(self):
        expected_scopes = set([
            "signing:format:gpg",
            "queue:define-task:buildbot-bridge/buildbot-bridge",
            "queue:create-task:buildbot-bridge/buildbot-bridge",
            "queue:task-priority:high",
        ])
        self.assertTrue(expected_scopes.issubset(self.graph["scopes"]))
