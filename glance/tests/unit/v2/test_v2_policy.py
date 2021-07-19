# Copyright 2021 Red Hat, Inc
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

import webob.exc

from glance.api.v2 import policy
from glance.common import exception
from glance.tests import utils


class APIPolicyBase(utils.BaseTestCase):
    def setUp(self):
        super(APIPolicyBase, self).setUp()
        self.enforcer = mock.MagicMock()
        self.context = mock.MagicMock()
        self.policy = policy.APIPolicyBase(self.context,
                                           enforcer=self.enforcer)

    def test_enforce(self):
        # Enforce passes
        self.policy._enforce('fake_rule')
        self.enforcer.enforce.assert_called_once_with(
            self.context,
            'fake_rule',
            mock.ANY)

        # Make sure that Forbidden gets caught and translated
        self.enforcer.enforce.side_effect = exception.Forbidden
        self.assertRaises(webob.exc.HTTPForbidden,
                          self.policy._enforce, 'fake_rule')

        # Any other exception comes straight through
        self.enforcer.enforce.side_effect = exception.ImageNotFound
        self.assertRaises(exception.ImageNotFound,
                          self.policy._enforce, 'fake_rule')

    def test_check(self):
        # Check passes
        self.assertTrue(self.policy.check('_enforce', 'fake_rule'))

        # Check fails
        self.enforcer.enforce.side_effect = exception.Forbidden
        self.assertFalse(self.policy.check('_enforce', 'fake_rule'))

    def test_check_is_image_mutable(self):
        context = mock.MagicMock()
        image = mock.MagicMock()

        # Admin always wins
        context.is_admin = True
        context.owner = 'someuser'
        self.assertIsNone(policy.check_is_image_mutable(context, image))

        # Image has no owner is never mutable by non-admins
        context.is_admin = False
        image.owner = None
        self.assertRaises(exception.Forbidden,
                          policy.check_is_image_mutable,
                          context, image)

        # Not owner is not mutable
        image.owner = 'someoneelse'
        self.assertRaises(exception.Forbidden,
                          policy.check_is_image_mutable,
                          context, image)

        # No project in context means not mutable
        image.owner = 'someoneelse'
        context.owner = None
        self.assertRaises(exception.Forbidden,
                          policy.check_is_image_mutable,
                          context, image)

        # Context matches image owner is mutable
        image.owner = 'someuser'
        context.owner = 'someuser'
        self.assertIsNone(policy.check_is_image_mutable(context, image))


class APIImagePolicy(APIPolicyBase):
    def setUp(self):
        super(APIImagePolicy, self).setUp()
        self.image = mock.MagicMock()
        self.policy = policy.ImageAPIPolicy(self.context, self.image,
                                            enforcer=self.enforcer)

    def test_enforce(self):
        self.assertRaises(webob.exc.HTTPNotFound,
                          super(APIImagePolicy, self).test_enforce)

    @mock.patch('glance.api.policy._enforce_image_visibility')
    def test_enforce_visibility(self, mock_enf):
        # Visibility passes
        self.policy._enforce_visibility('something')
        mock_enf.assert_called_once_with(self.enforcer,
                                         self.context,
                                         'something',
                                         mock.ANY)

        # Make sure that Forbidden gets caught and translated
        mock_enf.side_effect = exception.Forbidden
        self.assertRaises(webob.exc.HTTPForbidden,
                          self.policy._enforce_visibility, 'something')

        # Any other exception comes straight through
        mock_enf.side_effect = exception.ImageNotFound
        self.assertRaises(exception.ImageNotFound,
                          self.policy._enforce_visibility, 'something')

    def test_update_property(self):
        with mock.patch.object(self.policy, '_enforce') as mock_enf:
            self.policy.update_property('foo', None)
            mock_enf.assert_called_once_with('modify_image')

        with mock.patch.object(self.policy, '_enforce_visibility') as mock_enf:
            self.policy.update_property('visibility', 'foo')
            mock_enf.assert_called_once_with('foo')

    def test_update_locations(self):
        self.policy.update_locations()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'set_image_location',
                                                      mock.ANY)

    def test_delete_locations(self):
        self.policy.delete_locations()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'delete_image_location',
                                                      mock.ANY)

    def test_enforce_exception_behavior(self):
        with mock.patch.object(self.policy.enforcer, 'enforce') as mock_enf:
            # First make sure we can update if allowed
            self.policy.update_property('foo', None)
            self.assertTrue(mock_enf.called)

            # Make sure that if modify_image and get_image both return
            # Forbidden then we should get NotFound. This is because
            # we are not allowed to delete the image, nor see that it
            # even exists.
            mock_enf.reset_mock()
            mock_enf.side_effect = exception.Forbidden
            self.assertRaises(webob.exc.HTTPNotFound,
                              self.policy.update_property, 'foo', None)
            # Make sure we checked modify_image, and then get_image.
            mock_enf.assert_has_calls([
                mock.call(mock.ANY, 'modify_image', mock.ANY),
                mock.call(mock.ANY, 'get_image', mock.ANY)])

            # Make sure that if modify_image is disallowed, but
            # get_image is allowed, that we get Forbidden. This is
            # because we are allowed to see the image, but not modify
            # it, so 403 indicates that without confusing the user and
            # returning "not found" for an image they are able to GET.
            mock_enf.reset_mock()
            mock_enf.side_effect = [exception.Forbidden, lambda *a: None]
            self.assertRaises(webob.exc.HTTPForbidden,
                              self.policy.update_property, 'foo', None)
            # Make sure we checked modify_image, and then get_image.
            mock_enf.assert_has_calls([
                mock.call(mock.ANY, 'modify_image', mock.ANY),
                mock.call(mock.ANY, 'get_image', mock.ANY)])

    def test_get_image(self):
        self.policy.get_image()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'get_image',
                                                      mock.ANY)

    def test_get_images(self):
        self.policy.get_images()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'get_images',
                                                      mock.ANY)

    def test_delete_image(self):
        self.policy.delete_image()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'delete_image',
                                                      mock.ANY)

    def test_delete_image_falls_back_to_legacy(self):
        self.config(enforce_secure_rbac=False)

        # As admin, image is mutable even if owner does not match
        self.context.is_admin = True
        self.context.owner = 'someuser'
        self.image.owner = 'someotheruser'
        self.policy.delete_image()

        # As non-admin, owner matches, so we're good
        self.context.is_admin = False
        self.context.owner = 'someuser'
        self.image.owner = 'someuser'
        self.policy.delete_image()

        # If owner does not match, we fail
        self.image.owner = 'someotheruser'
        self.assertRaises(exception.Forbidden,
                          self.policy.delete_image)

        # Make sure we are checking the legacy handler
        with mock.patch('glance.api.v2.policy.check_is_image_mutable') as m:
            self.policy.delete_image()
            m.assert_called_once_with(self.context, self.image)

        # Make sure we are not checking it if enforce_secure_rbac=True
        self.config(enforce_secure_rbac=True)
        with mock.patch('glance.api.v2.policy.check_is_image_mutable') as m:
            self.policy.delete_image()
            self.assertFalse(m.called)


class TestMetadefAPIPolicy(APIPolicyBase):
    def setUp(self):
        super(TestMetadefAPIPolicy, self).setUp()
        self.enforcer = mock.MagicMock()
        self.md_resource = mock.MagicMock()
        self.context = mock.MagicMock()
        self.policy = policy.MetadefAPIPolicy(self.context, self.md_resource,
                                              enforcer=self.enforcer)

    def test_enforce(self):
        self.assertRaises(webob.exc.HTTPNotFound,
                          super(TestMetadefAPIPolicy, self).test_enforce)

    def test_get_metadef_namespace(self):
        self.policy.get_metadef_namespace()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'get_metadef_namespace',
                                                      mock.ANY)

    def test_get_metadef_namespaces(self):
        self.policy.get_metadef_namespaces()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'get_metadef_namespaces',
                                                      mock.ANY)

    def test_add_metadef_namespace(self):
        self.policy.add_metadef_namespace()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'add_metadef_namespace',
                                                      mock.ANY)

    def test_modify_metadef_namespace(self):
        self.policy.modify_metadef_namespace()
        self.enforcer.enforce.assert_called_once_with(
            self.context, 'modify_metadef_namespace', mock.ANY)

    def test_delete_metadef_namespace(self):
        self.policy.delete_metadef_namespace()
        self.enforcer.enforce.assert_called_once_with(
            self.context, 'delete_metadef_namespace', mock.ANY)

    def test_get_metadef_objects(self):
        self.policy.get_metadef_objects()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'get_metadef_objects',
                                                      mock.ANY)

    def test_get_metadef_object(self):
        self.policy.get_metadef_object()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'get_metadef_object',
                                                      mock.ANY)

    def test_add_metadef_object(self):
        self.policy.add_metadef_object()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'add_metadef_object',
                                                      mock.ANY)

    def test_modify_metadef_object(self):
        self.policy.modify_metadef_object()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'modify_metadef_object',
                                                      mock.ANY)

    def test_delete_metadef_object(self):
        self.policy.delete_metadef_object()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'delete_metadef_object',
                                                      mock.ANY)

    def test_add_metadef_tag(self):
        self.policy.add_metadef_tag()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'add_metadef_tag',
                                                      mock.ANY)

    def test_get_metadef_tags(self):
        self.policy.get_metadef_tags()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'get_metadef_tags',
                                                      mock.ANY)

    def test_delete_metadef_tags(self):
        self.policy.delete_metadef_tags()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'delete_metadef_tags',
                                                      mock.ANY)

    def test_add_metadef_property(self):
        self.policy.add_metadef_property()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'add_metadef_property',
                                                      mock.ANY)

    def test_get_metadef_properties(self):
        self.policy.get_metadef_properties()
        self.enforcer.enforce.assert_called_once_with(self.context,
                                                      'get_metadef_properties',
                                                      mock.ANY)

    def test_add_metadef_resource_type_association(self):
        self.policy.add_metadef_resource_type_association()
        self.enforcer.enforce.assert_called_once_with(
            self.context, 'add_metadef_resource_type_association', mock.ANY)

    def test_list_metadef_resource_types(self):
        self.policy.list_metadef_resource_types()
        self.enforcer.enforce.assert_called_once_with(
            self.context, 'list_metadef_resource_types', mock.ANY)

    def test_enforce_exception_behavior(self):
        with mock.patch.object(self.policy.enforcer, 'enforce') as mock_enf:
            # First make sure we can update if allowed
            self.policy.modify_metadef_namespace()
            self.assertTrue(mock_enf.called)

            # Make sure that if modify_metadef_namespace and
            # get_metadef_namespace both return Forbidden then we
            # should get NotFound. This is because we are not allowed
            # to modify the namespace, nor see that it even exists.
            mock_enf.reset_mock()
            mock_enf.side_effect = exception.Forbidden
            self.assertRaises(webob.exc.HTTPNotFound,
                              self.policy.modify_metadef_namespace)
            # Make sure we checked modify_metadef_namespace, and then
            # get_metadef_namespace.
            mock_enf.assert_has_calls([
                mock.call(mock.ANY, 'modify_metadef_namespace', mock.ANY),
                mock.call(mock.ANY, 'get_metadef_namespace', mock.ANY)])

            # Make sure that if modify_metadef_namespace is disallowed, but
            # get_metadef_namespace is allowed, that we get Forbidden. This is
            # because we are allowed to see the namespace, but not modify
            # it, so 403 indicates that without confusing the user and
            # returning "not found" for a namespace they are able to GET.
            mock_enf.reset_mock()
            mock_enf.side_effect = [exception.Forbidden, lambda *a: None]
            self.assertRaises(webob.exc.HTTPForbidden,
                              self.policy.modify_metadef_namespace)
            # Make sure we checked modify_metadef_namespace, and then
            # get_metadef_namespace.
            mock_enf.assert_has_calls([
                mock.call(mock.ANY, 'modify_metadef_namespace', mock.ANY),
                mock.call(mock.ANY, 'get_metadef_namespace', mock.ANY)])
