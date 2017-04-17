# Copyright (c) 2016 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import commands  # noqa
from os_xenapi.tests.plugins import plugin_test
try:
    import json
except ImportError:
    import simplejson as json

# global variable definition for fake arg
FAKE_ARG_DICT = {'id': 'fake_id', 'pub': 'fake_pub',
                 'enc_pass': 'fake_enc_pass',
                 'dom_id': 'fake_dom_id',
                 'url': 'fake_url',
                 'b64_path': 'fake_b64_path',
                 'b64_contents': 'fake_b64_contents',
                 'md5sum': 'fake_md5sum'}


class FakeTimeoutException(Exception):
    def __init__(self, details):
        self.details = details


class AgentTestCase(plugin_test.PluginTestBase):
    def setUp(self):
        super(AgentTestCase, self).setUp()
        self.agent = self.load_plugin("agent.py")
        self._wait_for_agent_original = self.agent._wait_for_agent
        self.mock_patch_object(self.agent,
                               '_wait_for_agent',
                               "fake_wait_agent_return")
        self.mock_patch_object(self.agent.xenstore,
                               'write_record',
                               'fake_write_recode_return')

    def test_version(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        tmp_arg_dict["value"] = json.dumps({"name": "version",
                                            "value": "agent"})
        request_id = tmp_arg_dict["id"]
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        self.agent.version(self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_version_timout_exception(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        tmp_arg_dict["value"] = json.dumps({"name": "version",
                                            "value": "agent"})
        request_id = tmp_arg_dict["id"]
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        side_effects = [FakeTimeoutException('TIME_OUT')]
        self.agent.PluginError = FakeTimeoutException
        self.agent._wait_for_agent.side_effect = side_effects
        self.assertRaises(self.agent.PluginError,
                          self.agent.version,
                          self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_key_init_ok(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        pub = tmp_arg_dict["pub"]
        tmp_arg_dict["value"] = json.dumps({"name": "keyinit",
                                            "value": pub})
        request_id = tmp_arg_dict["id"]
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        self.agent.key_init(self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_key_init_timout_exception(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        pub = tmp_arg_dict["pub"]
        tmp_arg_dict["value"] = json.dumps({"name": "keyinit",
                                            "value": pub})
        request_id = tmp_arg_dict["id"]
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        side_effects = [FakeTimeoutException('TIME_OUT')]
        self.agent.PluginError = FakeTimeoutException
        self.agent._wait_for_agent.side_effect = side_effects
        self.assertRaises(self.agent.PluginError,
                          self.agent.key_init,
                          self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_password_ok(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        enc_pass = tmp_arg_dict["enc_pass"]
        tmp_arg_dict["value"] = json.dumps({"name": "password",
                                            "value": enc_pass})
        request_id = tmp_arg_dict["id"]
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        self.agent.password(self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_password_timout_exception(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        enc_pass = tmp_arg_dict["enc_pass"]
        tmp_arg_dict["value"] = json.dumps({"name": "password",
                                            "value": enc_pass})
        request_id = tmp_arg_dict["id"]
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        side_effects = [FakeTimeoutException('TIME_OUT')]
        self.agent.PluginError = FakeTimeoutException
        self.agent._wait_for_agent.side_effect = side_effects
        self.assertRaises(self.agent.PluginError,
                          self.agent.password,
                          self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_reset_network_ok(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        tmp_arg_dict['value'] = json.dumps({'name': 'resetnetwork',
                                            'value': ''})
        request_id = tmp_arg_dict['id']
        tmp_arg_dict['path'] = "data/host/%s" % request_id
        self.agent.resetnetwork(self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_reset_network_timout_exception(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        tmp_arg_dict['value'] = json.dumps({'name': 'resetnetwork',
                                            'value': ''})
        request_id = tmp_arg_dict['id']
        tmp_arg_dict['path'] = "data/host/%s" % request_id
        side_effects = [FakeTimeoutException('TIME_OUT')]
        self.agent.PluginError = FakeTimeoutException
        self.agent._wait_for_agent.side_effect = side_effects
        self.assertRaises(self.agent.PluginError,
                          self.agent.resetnetwork,
                          self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_inject_file_with_dict_value(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        request_id = tmp_arg_dict["id"]
        b64_path = tmp_arg_dict["b64_path"]
        b64_file = tmp_arg_dict["b64_contents"]
        self.mock_patch_object(self.agent.base64,
                               'b64decode',
                               'fake_decode_b64')
        self.mock_patch_object(self.agent.base64,
                               'b64encode',
                               'fake_encode_b64')
        self.mock_patch_object(self.agent,
                               '_get_agent_features',
                               'file_inject')
        tmp_arg_dict["value"] = json.dumps({"name": "file_inject",
                                            "value": {"b64_path": b64_path,
                                                      "b64_file": b64_file}})
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        self.agent.inject_file(self.agent, FAKE_ARG_DICT)
        self.agent.base64.b64decode.assert_not_called()
        self.agent.base64.b64encode.assert_not_called()
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)
        self.agent._get_agent_features.assert_called_once()

    def test_inject_file_with_combined_str_value(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        request_id = tmp_arg_dict["id"]
        self.mock_patch_object(self.agent.base64,
                               'b64decode',
                               'fake_decode_b64')
        self.mock_patch_object(self.agent.base64,
                               'b64encode',
                               'fake_encode_b64')
        self.mock_patch_object(self.agent,
                               '_get_agent_features',
                               'injectfile')
        tmp_arg_dict["value"] = json.dumps({"name": "injectfile",
                                            "value": 'fake_encode_b64'})
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        self.agent.inject_file(self.agent, FAKE_ARG_DICT)
        self.agent.base64.b64decode.assert_called()
        self.agent.base64.b64encode.assert_called_once()
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)
        self.agent._get_agent_features.assert_called_once()

    def test_inject_file_NotImp_exception(self):
        self.mock_patch_object(self.agent,
                               '_get_agent_features',
                               'fake_not_imp_exp')
        self.assertRaises(NotImplementedError,
                          self.agent.inject_file,
                          self.agent, FAKE_ARG_DICT)
        self.agent._get_agent_features.assert_called_once()

    def test_inject_file_Timeout_exception(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        request_id = tmp_arg_dict["id"]
        b64_path = tmp_arg_dict["b64_path"]
        b64_file = tmp_arg_dict["b64_contents"]
        tmp_arg_dict["value"] = json.dumps({"name": "file_inject",
                                            "value": {"b64_path": b64_path,
                                                      "b64_file": b64_file}})
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        self.mock_patch_object(self.agent,
                               '_get_agent_features',
                               'file_inject')
        side_effects = [FakeTimeoutException('TIME_OUT')]
        self.agent.PluginError = FakeTimeoutException
        self.agent._wait_for_agent.side_effect = side_effects
        self.assertRaises(self.agent.PluginError,
                          self.agent.inject_file,
                          self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_agent_update_ok(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        request_id = tmp_arg_dict["id"]
        url = tmp_arg_dict["url"]
        md5sum = tmp_arg_dict["md5sum"]
        tmp_arg_dict["value"] = json.dumps({"name": "agentupdate",
                                            "value": "%s,%s" % (url, md5sum)})
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        self.agent.agent_update(self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_with(self.agent,
                                                            tmp_arg_dict)

    def test_agent_update_timout_exception(self):
        tmp_arg_dict = FAKE_ARG_DICT
        tmp_arg_dict.pop('timeout', self.agent.DEFAULT_TIMEOUT)
        request_id = tmp_arg_dict["id"]
        url = tmp_arg_dict["url"]
        md5sum = tmp_arg_dict["md5sum"]
        tmp_arg_dict["value"] = json.dumps({"name": "agentupdate",
                                            "value": "%s,%s" % (url, md5sum)})
        tmp_arg_dict["path"] = "data/host/%s" % request_id
        side_effects = [FakeTimeoutException('TIME_OUT')]
        self.agent.PluginError = FakeTimeoutException
        self.agent._wait_for_agent.side_effect = side_effects
        self.assertRaises(self.agent.PluginError,
                          self.agent.agent_update,
                          self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_once()

    def test_get_agent_features_returncode_0(self):
        self.mock_patch_object(self.agent.json,
                               'loads',
                               {'returncode': 0})
        featrues_ret = self.agent._get_agent_features(self.agent,
                                                      FAKE_ARG_DICT)
        self.assertFalse(bool(featrues_ret))
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_once()

    def test_get_agent_features_returncode_not_0(self):
        self.mock_patch_object(self.agent,
                               '_wait_for_agent',
                               'fake_wait_agent_return')
        self.mock_patch_object(self.agent.json,
                               'loads',
                               {'returncode': 'fake_return_code',
                                'message': 'fake_message'})
        featrues_ret = self.agent._get_agent_features(self.agent,
                                                      FAKE_ARG_DICT)
        self.assertTrue(bool(featrues_ret))
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_once()

    def test_get_agent_features_timout_exception(self):
        side_effects = [FakeTimeoutException('TIME_OUT')]
        self.agent.PluginError = FakeTimeoutException
        self.agent._wait_for_agent.side_effect = side_effects
        self.assertRaises(self.agent.PluginError,
                          self.agent._get_agent_features,
                          self.agent, FAKE_ARG_DICT)
        self.agent._wait_for_agent.assert_called_once()
        self.agent.xenstore.write_record.assert_called_once()

    def test_wait_for_agent_ok(self):
        self.agent._wait_for_agent = self._wait_for_agent_original
        self.mock_patch_object(self.agent.xenstore,
                               'read_record',
                               'fake_read_record')
        self.agent._wait_for_agent(self,
                                   'fake_id',
                                   FAKE_ARG_DICT,
                                   self.agent.DEFAULT_TIMEOUT)
        self.agent.xenstore.read_record.assert_called_once()
        self.assertNotEqual(self.agent._wait_for_agent, '"None"')

    def test_wait_for_agent_reboot_detected_exception(self):
        self.agent._wait_for_agent = self._wait_for_agent_original
        self.mock_patch_object(self.agent.xenstore,
                               'read_record',
                               '"None"')
        self.mock_patch_object(self.agent.xenstore,
                               'record_exists',
                               False)
        self.mock_patch_object(self.agent.xenstore,
                               'delete_record',
                               'fake_del_record')
        self.assertRaises(self.agent.RebootDetectedError,
                          self.agent._wait_for_agent,
                          'host_ref', 'fake_id', FAKE_ARG_DICT,
                          self.agent.DEFAULT_TIMEOUT)
        self.agent.xenstore.read_record.assert_called_once()
        self.agent.xenstore.delete_record.assert_called_once()

    def test_wait_for_agent_timeout_exception(self):
        self.agent._wait_for_agent = self._wait_for_agent_original
        self.mock_patch_object(self.agent.xenstore,
                               'read_record',
                               '"None"')
        self.mock_patch_object(self.agent.xenstore,
                               'record_exists',
                               True)
        self.mock_patch_object(self.agent.xenstore,
                               'delete_record',
                               'fake_del_record')
        self.assertRaises(self.agent.TimeoutError,
                          self.agent._wait_for_agent,
                          'host_ref', 'fake_id', FAKE_ARG_DICT,
                          self.agent.DEFAULT_TIMEOUT)
        self.agent.xenstore.read_record.assert_called()
        self.agent.xenstore.delete_record.assert_called_once()
