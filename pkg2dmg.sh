#!/bin/bash

mydir=$(dirname $(realpath $0))
cd $mydir
# create macos g3mclass.app
python3 setup.py sdist
v=$(cat g3mclass/version.txt)
rm -rf dmg/ # clean up
mkdir -p dmg/install.app/Contents/MacOS
mkdir -p dmg/install.app/Contents/Resources
cp dist/g3mclass-$v.tar.gz dmg/install.app/Contents/Resources/

# create install script
cat <<EOF >dmg/install.app/Contents/MacOS/install
#!/bin/sh
p=\$(dirname \$BASH_SOURCE)
python3 -m pip install --user -U "\$p"/../Resources/g3mclass-$v.tar.gz
cp -r "\$p"/../Resources/g3mclass.app \$HOME/Applications/
ln -sf \$HOME/Applications/g3mclass.app \$HOME/Desktop/
EOF
chmod 755 dmg/install.app/Contents/MacOS/install

# create execution app to be copied to $HOME/Application
dgapp=dmg/install.app/Contents/Resources/g3mclass.app/Contents/MacOS/
mkdir -p $dgapp
cat >$dgapp/g3mclass <<EOF
#!/bin/sh
base=\$(python3 -m site --user-base)
\$base/bin/g3mclass
EOF
chmod 755 $dgapp/g3mclass

# create uninstall script
mkdir -p dmg/uninstall.app/Contents/MacOS
cat >dmg/uninstall.app/Contents/MacOS/uninstall <<EOF
#!/bin/sh
python3 -m pip uninstall -y g3mclass
rm -rf \$HOME/Applications/g3mclass.app
rm -f \$HOME/Desktop/g3mclass.app
EOF
chmod 755 dmg/uninstall.app/Contents/MacOS/uninstall

# create/format a dmg
rm -f dist/g3mclass-$v.dmg
s=$(echo -e $(($(du -sk dmg | cut -f1)+10))"\n"512 | sort -n | tail -1)
dd if=/dev/zero of=dist/g3mclass-$v.dmg bs=1k count=$s status=progress
mkfs.hfsplus -v install_g3mclass-$v dist/g3mclass-$v.dmg

# copy files into image fs
mount | grep /mnt/disk && sudo umount /mnt/disk
sudo mount -o loop dist/g3mclass-$v.dmg /mnt/disk
sudo cp -av dmg/* /mnt/disk
sudo umount /mnt/disk

# compress
/usr/local/src/libdmg-hfsplus-only_what_core_needs/build/dmg/dmg dist/g3mclass-$v.dmg dist/g3mclass-$v.c.dmg && \
mv -f dist/g3mclass-$v.c.dmg dist/g3mclass-$v.dmg
