# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

    # define the box
    config.vm.box = "bento/ubuntu-16.04"

    config.vm.hostname = "pp"

    # Create a forwarded port mapping which allows access to a specific port
    # within the machine from a port on the host machine. In the example below,
    # accessing "localhost:8000" will access port 80 on the guest machine.
    config.vm.network :forwarded_port, host: 7700, guest: 18000
    config.vm.network :forwarded_port, host: 1080, guest: 1080

    # Create a public network, which generally matched to bridged network.
    # Bridged networks make the machine appear as another physical device on
    # your network.
    # config.vm.network "public_network"
    # config.vm.network "private_network", type: "dhcp"

    config.vm.boot_timeout = 500

    # If true, then any SSH connections made will enable agent forwarding.
    # Default value: false
    config.ssh.forward_agent = true

    # set up synced folders
    config.vm.synced_folder ".", "/src/poleperformance"

    #config.vm.provider "virtualbox" do |vb|
    #  vb.gui = true
    #end

    # ansible provisioning
    config.vm.provision "ansible" do |ansible|
      ansible.playbook = "ansible/vagrant.yml"
      ansible.vault_password_file = "ansible/.vaultpass"
      ansible.verbose = "vv"
    end

# For setting up heroku push
#   config.push.define "heroku" do |push|
#    push.app = "tranquil-oasis-6724"

end

