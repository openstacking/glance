# Copyright 2020 Red Hat, Inc.
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

from unittest import mock

from glance.api import authorization
from glance.api import property_protections
from glance import context
from glance import gateway
from glance import notifier
from glance.tests.unit import utils as unit_test_utils
import glance.tests.utils as test_utils


class TestGateway(test_utils.BaseTestCase):
    def setUp(self):
        super(TestGateway, self).setUp()
        self.gateway = gateway.Gateway()
        self.context = mock.sentinel.context

    @mock.patch('glance.domain.TaskExecutorFactory')
    def test_get_task_executor_factory(self, mock_factory):
        @mock.patch.object(self.gateway, 'get_task_repo')
        @mock.patch.object(self.gateway, 'get_repo')
        @mock.patch.object(self.gateway, 'get_image_factory')
        def _test(mock_gif, mock_gr, mock_gtr):
            self.gateway.get_task_executor_factory(self.context)
            mock_gtr.assert_called_once_with(self.context)
            mock_gr.assert_called_once_with(self.context)
            mock_gif.assert_called_once_with(self.context)
            mock_factory.assert_called_once_with(
                mock_gtr.return_value,
                mock_gr.return_value,
                mock_gif.return_value,
                admin_repo=None)

        _test()

    @mock.patch('glance.domain.TaskExecutorFactory')
    def test_get_task_executor_factory_with_admin(self, mock_factory):
        @mock.patch.object(self.gateway, 'get_task_repo')
        @mock.patch.object(self.gateway, 'get_repo')
        @mock.patch.object(self.gateway, 'get_image_factory')
        def _test(mock_gif, mock_gr, mock_gtr):
            mock_gr.side_effect = [mock.sentinel.image_repo,
                                   mock.sentinel.admin_repo]
            self.gateway.get_task_executor_factory(
                self.context,
                admin_context=mock.sentinel.admin_context)
            mock_gtr.assert_called_once_with(self.context)
            mock_gr.assert_has_calls([
                mock.call(self.context),
                mock.call(mock.sentinel.admin_context),
            ])
            mock_gif.assert_called_once_with(self.context)
            mock_factory.assert_called_once_with(
                mock_gtr.return_value,
                mock.sentinel.image_repo,
                mock_gif.return_value,
                admin_repo=mock.sentinel.admin_repo)

        _test()

    @mock.patch('glance.api.policy.ImageRepoProxy')
    def test_get_repo(self, mock_proxy):
        repo = self.gateway.get_repo(self.context)
        self.assertIsInstance(repo, authorization.ImageRepoProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.ImageRepoProxy')
    def test_get_repo_without_auth(self, mock_proxy):
        repo = self.gateway.get_repo(self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.ImageRepoProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.common.property_utils.PropertyRules._load_rules')
    def test_get_repo_without_auth_with_pp(self, mock_load):
        self.config(property_protection_file='foo')
        repo = self.gateway.get_repo(self.context, authorization_layer=False)
        self.assertIsInstance(repo,
                              property_protections.ProtectedImageRepoProxy)

    def test_get_repo_member_property(self):
        """Test that the image.member property is propagated all the way from
        the DB to the top of the gateway repo stack.
        """
        db_api = unit_test_utils.FakeDB()
        gw = gateway.Gateway(db_api=db_api)

        # Get the UUID1 image as TENANT1
        ctxt = context.RequestContext(tenant=unit_test_utils.TENANT1)
        repo = gw.get_repo(ctxt)
        image = repo.get(unit_test_utils.UUID1)
        # We own the image, so member is None
        self.assertIsNone(image.member)

        # Get the UUID1 image as TENANT2
        ctxt = context.RequestContext(tenant=unit_test_utils.TENANT2)
        repo = gw.get_repo(ctxt)
        image = repo.get(unit_test_utils.UUID1)
        # We are a member, so member is our tenant id
        self.assertEqual(unit_test_utils.TENANT2, image.member)

    @mock.patch('glance.api.policy.MetadefNamespaceRepoProxy')
    def test_get_namespace_repo(self, mock_proxy):
        repo = self.gateway.get_metadef_namespace_repo(self.context)
        self.assertIsInstance(repo, authorization.MetadefNamespaceRepoProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefNamespaceFactoryProxy')
    def test_get_namespace_repo_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_namespace_repo(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefNamespaceRepoProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.api.policy.MetadefNamespaceFactoryProxy')
    def test_get_namespace_factory(self, mock_proxy):
        repo = self.gateway.get_metadef_namespace_factory(self.context)
        self.assertIsInstance(repo,
                              authorization.MetadefNamespaceFactoryProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefNamespaceFactoryProxy')
    def test_get_namespace_factory_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_namespace_factory(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefNamespaceFactoryProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.api.policy.MetadefObjectRepoProxy')
    def test_get_object_repo(self, mock_proxy):
        repo = self.gateway.get_metadef_object_repo(self.context)
        self.assertIsInstance(repo, authorization.MetadefObjectRepoProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefObjectRepoProxy')
    def test_get_object_repo_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_object_repo(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefObjectRepoProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.api.policy.MetadefObjectFactoryProxy')
    def test_get_object_factory(self, mock_proxy):
        repo = self.gateway.get_metadef_object_factory(self.context)
        self.assertIsInstance(repo,
                              authorization.MetadefObjectFactoryProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefObjectFactoryProxy')
    def test_get_object_factory_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_object_factory(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefObjectFactoryProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.api.policy.MetadefResourceTypeRepoProxy')
    def test_get_resourcetype_repo(self, mock_proxy):
        repo = self.gateway.get_metadef_resource_type_repo(self.context)
        self.assertIsInstance(repo, authorization.MetadefResourceTypeRepoProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefResourceTypeRepoProxy')
    def test_get_resourcetype_repo_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_resource_type_repo(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefResourceTypeRepoProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.api.policy.MetadefResourceTypeFactoryProxy')
    def test_get_resource_type_factory(self, mock_proxy):
        repo = self.gateway.get_metadef_resource_type_factory(self.context)
        self.assertIsInstance(repo,
                              authorization.MetadefResourceTypeFactoryProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefResourceTypeFactoryProxy')
    def test_get_resource_type_factory_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_resource_type_factory(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefResourceTypeFactoryProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.api.policy.MetadefPropertyRepoProxy')
    def test_get_property_repo(self, mock_proxy):
        repo = self.gateway.get_metadef_property_repo(self.context)
        self.assertIsInstance(repo,
                              authorization.MetadefPropertyRepoProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefPropertyRepoProxy')
    def test_get_property_repo_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_property_repo(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefPropertyRepoProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.api.policy.MetadefPropertyFactoryProxy')
    def test_get_property_factory(self, mock_proxy):
        repo = self.gateway.get_metadef_property_factory(self.context)
        self.assertIsInstance(repo, authorization.MetadefPropertyFactoryProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefPropertyFactoryProxy')
    def test_get_property_factory_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_property_factory(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefPropertyFactoryProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.api.policy.MetadefTagRepoProxy')
    def test_get_tag_repo(self, mock_proxy):
        repo = self.gateway.get_metadef_tag_repo(self.context)
        self.assertIsInstance(repo, authorization.MetadefTagRepoProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefTagRepoProxy')
    def test_get_tag_repo_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_tag_repo(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefTagRepoProxy)
        mock_proxy.assert_not_called()

    @mock.patch('glance.api.policy.MetadefTagFactoryProxy')
    def test_get_tag_factory(self, mock_proxy):
        repo = self.gateway.get_metadef_tag_factory(self.context)
        self.assertIsInstance(repo, authorization.MetadefTagFactoryProxy)
        mock_proxy.assert_called_once_with(mock.ANY, mock.sentinel.context,
                                           mock.ANY)

    @mock.patch('glance.api.policy.MetadefTagFactoryProxy')
    def test_get_tag_factory_without_auth(self, mock_proxy):
        repo = self.gateway.get_metadef_tag_factory(
            self.context, authorization_layer=False)
        self.assertIsInstance(repo, notifier.MetadefTagFactoryProxy)
        mock_proxy.assert_not_called()
