#!/bin/bash

DEBIAN_CLONE_DIR="debian-${TRAVIS_COMMIT}"

git clone -b debian --single-branch --depth=1 \
    https://github.com/${TRAVIS_REPO_SLUG}.git ${DEBIAN_CLONE_DIR} \
&& cp -r ${DEBIAN_CLONE_DIR}/debian . \
&& docker-compose exec -T tango-test gbp dch --upstream-branch=master \
    --ignore-branch --debian-tag='v%(version)s' \
    --spawn-editor=never --distribution=unknown --force-distribution \
    -N ${TRAVIS_TAG#v} --release \
&& docker-compose exec -T tango-test debuild -b -us -uc \
&& docker-compose exec -T tango-test bash -c "cp ../*.deb ." \
&& cp debian/changelog ${DEBIAN_CLONE_DIR}/debian/changelog \
&& cd ${DEBIAN_CLONE_DIR} \
&& git config --global user.email "travis@travis-ci.org" \
&& git config --global user.name "Travis CI" \
&& git commit -m "New release ${TRAVIS_TAG}" debian/changelog \
&& git remote add origin-debian https://${GH_TOKEN}@github.com/${TRAVIS_REPO_SLUG}.git > /dev/null 2>&1 \
&& git push --quiet --set-upstream origin-debian debian \
&& cd ..
