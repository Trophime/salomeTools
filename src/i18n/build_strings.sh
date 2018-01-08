#!/bin/bash

# This script gets the strings from code to internationalize from the source code

I18HOME=`dirname $0`
SRC_DIR=$I18HOME/../..

# get strings for french translation
echo "Build strings for French, create and merging salomeTools.po" 

poFile=$I18HOME/fr/LC_MESSAGES/salomeTools.po
refFile=$I18HOME/fr/LC_MESSAGES/ref.pot

xgettext $SRC_DIR/*.py $SRC_DIR/commands/*.py $SRC_DIR/src/*.py \
    --no-wrap --no-location --language=Python --omit-header \
    --output=$refFile

msgmerge --quiet --update $poFile $refFile

#retirer les messages obsolètes « #~ »
#msgattrib --no-obsolete -o $poFile $poFile

#ne pas retirer les messages obsolètes « #~ »
msgattrib --previous --output-file $poFile $poFile

rm $refFile

echo "Do not forget 'translate.py' or 'translate.sh' to create salomeTools.mo"

