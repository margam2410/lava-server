import os
import yaml
import tempfile
from lava_scheduler_app.utils import split_multinode_yaml
from lava_scheduler_app.dbutils import match_vlan_interface
from lava_scheduler_app.models import (
    Device,
    DeviceDictionary,
    TestJob,
    Tag,
)
from lava_scheduler_app.utils import (
    devicedictionary_to_jinja2,
    prepare_jinja_template,
)
from lava_scheduler_app.tests.test_submission import TestCaseWithFactory
from lava_scheduler_app.tests.test_pipeline import YamlFactory
from lava_scheduler_app.dbutils import find_device_for_job
from lava_dispatcher.pipeline.device import NewDevice
from lava_dispatcher.pipeline.parser import JobParser
from lava_dispatcher.pipeline.protocols.vland import VlandProtocol
from lava_dispatcher.pipeline.protocols.multinode import MultinodeProtocol

# pylint does not like TestCaseWithFactory
# pylint: disable=too-many-ancestors,no-self-use


class VlandFactory(YamlFactory):

    def __init__(self):
        super(VlandFactory, self).__init__()
        self.bbb1 = None
        self.cubie1 = None

    def setUp(self):  # pylint: disable=invalid-name
        bbb_type = self.make_device_type(name='bbb')
        cubie_type = self.make_device_type(name='cubietruck')
        self.bbb1 = self.make_device(bbb_type, hostname='bbb1')
        self.cubie1 = self.make_device(cubie_type, hostname='cubie1')

    def make_vland_job(self, **kw):
        sample_job_file = os.path.join(os.path.dirname(__file__), 'bbb-cubie-vlan-group.yaml')
        with open(sample_job_file, 'r') as test_support:
            data = yaml.load(test_support)
        data.update(kw)
        return data


class TestVlandSplit(TestCaseWithFactory):
    """
    Test the splitting of lava-vland data from submission YAML
    Same tests as test_submission but converted to use and look for YAML.
    """
    def setUp(self):
        super(TestVlandSplit, self).setUp()
        self.factory = VlandFactory()

    def test_split_vland(self):
        target_group = "unit-test-only"
        job_dict = split_multinode_yaml(self.factory.make_vland_job(), target_group)
        self.assertEqual(len(job_dict), 2)
        roles = job_dict.keys()
        self.assertEqual({'server', 'client'}, set(roles))
        for role in roles:
            self.assertEqual(len(job_dict[role]), 1)  # count = 1
        client_job = job_dict['client'][0]
        server_job = job_dict['server'][0]
        self.assertIn('lava-multinode', client_job['protocols'])
        self.assertIn('lava-multinode', server_job['protocols'])
        self.assertIn('lava-vland', client_job['protocols'])
        self.assertIn('lava-vland', server_job['protocols'])
        client_vlan = client_job['protocols']['lava-vland']
        server_vlan = server_job['protocols']['lava-vland']
        self.assertIn('vlan_one', client_vlan)
        self.assertIn('vlan_two', server_vlan)
        self.assertEqual(['10G'], client_vlan.values()[0]['tags'])
        self.assertEqual(['1G'], server_vlan.values()[0]['tags'])


class TestVlandDevices(TestCaseWithFactory):
    """
    Test the matching of vland device requirements with submission YAML
    """
    def setUp(self):
        super(TestVlandDevices, self).setUp()
        self.factory = VlandFactory()
        self.factory.setUp()

    def test_match_devices_without_map(self):
        devices = Device.objects.filter(status=Device.IDLE).order_by('is_public')
        self.factory.ensure_tag('usb-eth')
        self.factory.ensure_tag('sata')
        self.factory.bbb1.tags = Tag.objects.filter(name='usb-eth')
        self.factory.bbb1.save()
        self.factory.cubie1.tags = Tag.objects.filter(name='sata')
        self.factory.cubie1.save()
        user = self.factory.make_user()
        sample_job_file = os.path.join(os.path.dirname(__file__), 'bbb-cubie-vlan-group.yaml')
        with open(sample_job_file, 'r') as test_support:
            data = yaml.load(test_support)
        vlan_job = TestJob.from_yaml_and_user(yaml.dump(data), user)
        assignments = {}
        for job in vlan_job:
            device = find_device_for_job(job, devices)
            self.assertEqual(device.device_type, job.requested_device_type)
            # no map defined
            self.assertFalse(match_vlan_interface(device, yaml.load(job.definition)))
            assignments[job.device_role] = device
        self.assertEqual(assignments['client'].hostname, self.factory.bbb1.hostname)
        self.assertEqual(assignments['server'].hostname, self.factory.cubie1.hostname)

    def test_jinja_template(self):
        jinja2_path = os.path.realpath(os.path.join(
            __file__, '..', '..', '..', 'etc', 'dispatcher-config'))
        self.assertTrue(os.path.exists(jinja2_path))
        device_dict = DeviceDictionary(hostname=self.factory.bbb1.hostname)
        device_dict.parameters = {
            'interfaces': ['eth0', 'eth1'],
            'sysfs': {
                'eth0': "/sys/devices/pci0000:00/0000:00:19.0/net/eth0",
                'eth1': "/sys/devices/pci0000:00/0000:00:1c.1/0000:03:00.0/net/eth1"},
            'mac_addr': {'eth0': "f0:de:f1:46:8c:21", 'eth1': "00:24:d7:9b:c0:8c"},
            'tags': {'eth0': ['1G', '10G'], 'eth1': ['1G']},
            'map': {'eth0': {'192.168.0.2': 5}, 'eth1': {'192.168.0.2': 7}}
        }
        #  {% map = '{'eth1': {'3': 8}, 'eth0': {'3': 19}}' %}
        device_dict.save()
        data = devicedictionary_to_jinja2(device_dict.parameters, 'beaglebone-black.jinja2')
        check_str = """{% extends 'beaglebone-black.jinja2' %}
{% set map = {'eth0': {'192.168.0.2': 5}, 'eth1': {'192.168.0.2': 7}} %}
{% set interfaces = ['eth0', 'eth1'] %}
{% set sysfs = {'eth0': '/sys/devices/pci0000:00/0000:00:19.0/net/eth0',
'eth1': '/sys/devices/pci0000:00/0000:00:1c.1/0000:03:00.0/net/eth1'} %}
{% set mac_addr = {'eth0': 'f0:de:f1:46:8c:21', 'eth1': '00:24:d7:9b:c0:8c'} %}
{% set tags = {'eth0': ['1G', '10G'], 'eth1': ['1G']} %}
"""
        self.assertEqual(check_str, data)
        template = prepare_jinja_template(self.factory.bbb1.hostname, data, system_path=False)
        device_configuration = template.render()
        yaml_data = yaml.load(device_configuration)
        self.assertIn('parameters', yaml_data)
        self.assertIn('interfaces', yaml_data['parameters'])
        self.assertIn('bootm', yaml_data['parameters'])
        self.assertIn('bootz', yaml_data['parameters'])
        self.assertIn('actions', yaml_data)
        self.assertIn('eth0', yaml_data['parameters']['interfaces'])
        self.assertIn('eth1', yaml_data['parameters']['interfaces'])
        self.assertIn('sysfs', yaml_data['parameters']['interfaces']['eth0'])
        self.assertEqual(
            '/sys/devices/pci0000:00/0000:00:1c.1/0000:03:00.0/net/eth1',
            yaml_data['parameters']['interfaces']['eth1']['sysfs']
        )

    def test_match_devices_with_map(self):
        devices = Device.objects.filter(status=Device.IDLE).order_by('is_public')
        self.factory.ensure_tag('usb-eth')
        self.factory.ensure_tag('sata')
        self.factory.bbb1.tags = Tag.objects.filter(name='usb-eth')
        self.factory.bbb1.save()
        self.factory.cubie1.tags = Tag.objects.filter(name='sata')
        self.factory.cubie1.save()
        device_dict = DeviceDictionary(hostname=self.factory.bbb1.hostname)
        device_dict.parameters = {
            'interfaces': ['eth0', 'eth1'],
            'sysfs': {
                'eth0': "/sys/devices/pci0000:00/0000:00:19.0/net/eth0",
                'eth1': "/sys/devices/pci0000:00/0000:00:1c.1/0000:03:00.0/net/eth1"},
            'mac_addr': {'eth0': "f0:de:f1:46:8c:21", 'eth1': "00:24:d7:9b:c0:8c"},
            'tags': {'eth0': ['1G', '10G'], 'eth1': ['1G']},
            'map': {'eth0': {'192.168.0.2': 5}, 'eth1': {'192.168.0.2': 7}}
        }
        device_dict.save()
        device_dict = DeviceDictionary(hostname=self.factory.cubie1.hostname)
        device_dict.parameters = {
            'interfaces': ['eth0', 'eth1'],
            'sysfs': {
                'eth0': "/sys/devices/pci0000:00/0000:00:19.0/net/eth0",
                'eth1': "/sys/devices/pci0000:00/0000:00:1c.1/0000:03:00.0/net/eth1"},
            'mac_addr': {'eth0': "f0:de:f1:46:8c:21", 'eth1': "00:24:d7:9b:c0:8c"},
            'tags': {'eth0': ['1G', '10G'], 'eth1': ['1G']},
            'map': {'eth0': {'192.168.0.2': 4}, 'eth1': {'192.168.0.2': 6}}
        }
        device_dict.save()
        user = self.factory.make_user()
        sample_job_file = os.path.join(os.path.dirname(__file__), 'bbb-cubie-vlan-group.yaml')
        with open(sample_job_file, 'r') as test_support:
            data = yaml.load(test_support)
        vlan_job = TestJob.from_yaml_and_user(yaml.dump(data), user)
        assignments = {}
        for job in vlan_job:
            device = find_device_for_job(job, devices)
            self.assertEqual(device.device_type, job.requested_device_type)
            # map has been defined
            self.assertTrue(match_vlan_interface(device, yaml.load(job.definition)))
            assignments[job.device_role] = device
        self.assertEqual(assignments['client'].hostname, self.factory.bbb1.hostname)
        self.assertEqual(assignments['server'].hostname, self.factory.cubie1.hostname)


class TestVlandProtocolSplit(TestCaseWithFactory):
    """
    Test the handling of protocols in dispatcher after splitting the YAML
    """
    def setUp(self):
        super(TestVlandProtocolSplit, self).setUp()
        self.factory = VlandFactory()
        self.factory.setUp()

    def test_job_protocols(self):
        self.factory.ensure_tag('usb-eth')
        self.factory.ensure_tag('sata')
        self.factory.bbb1.tags = Tag.objects.filter(name='usb-eth')
        self.factory.bbb1.save()
        self.factory.cubie1.tags = Tag.objects.filter(name='sata')
        self.factory.cubie1.save()
        device_dict = DeviceDictionary(hostname=self.factory.bbb1.hostname)
        device_dict.parameters = {
            'interfaces': ['eth0', 'eth1'],
            'sysfs': {
                'eth0': "/sys/devices/pci0000:00/0000:00:19.0/net/eth0",
                'eth1': "/sys/devices/pci0000:00/0000:00:1c.1/0000:03:00.0/net/eth1"},
            'mac_addr': {'eth0': "f0:de:f1:46:8c:21", 'eth1': "00:24:d7:9b:c0:8c"},
            'tags': {'eth0': ['1G', '10G'], 'eth1': ['1G']},
            'map': {'eth0': {'192.168.0.2': 5}, 'eth1': {'192.168.0.2': 7}}
        }
        device_dict.save()
        device_dict = DeviceDictionary(hostname=self.factory.cubie1.hostname)
        device_dict.parameters = {
            'interfaces': ['eth0', 'eth1'],
            'sysfs': {
                'eth0': "/sys/devices/pci0000:00/0000:00:19.0/net/eth0",
                'eth1': "/sys/devices/pci0000:00/0000:00:1c.1/0000:03:00.0/net/eth1"},
            'mac_addr': {'eth0': "f0:de:f1:46:8c:21", 'eth1': "00:24:d7:9b:c0:8c"},
            'tags': {'eth0': ['1G', '10G'], 'eth1': ['1G']},
            'map': {'eth0': {'192.168.0.2': 4}, 'eth1': {'192.168.0.2': 6}}
        }
        device_dict.save()
        target_group = "unit-test-only"
        job_dict = split_multinode_yaml(self.factory.make_vland_job(), target_group)
        client_job = job_dict['client'][0]
        client_handle, client_file_name = tempfile.mkstemp()
        yaml.dump(client_job, open(client_file_name, 'w'))
        # YAML device file, as required by lava-dispatch --target
        device_yaml_file = os.path.realpath(os.path.join(os.path.dirname(__file__), 'bbb-01.yaml'))
        self.assertTrue(os.path.exists(device_yaml_file))
        parser = JobParser()
        bbb_device = NewDevice(device_yaml_file)
        with open(client_file_name) as sample_job_data:
            bbb_job = parser.parse(sample_job_data, bbb_device, 4212, None, None, None, output_dir='/tmp/')
        os.close(client_handle)
        os.unlink(client_file_name)
        self.assertIn('protocols', bbb_job.parameters)
        self.assertIn(VlandProtocol.name, bbb_job.parameters['protocols'])
        self.assertIn(MultinodeProtocol.name, bbb_job.parameters['protocols'])
