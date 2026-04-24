#!/bin/bash

destination_folder="$HOME/.config/legcord/plugins/1loader/dist"
if [ "$EQUICORD" == "1" ]; then
    source_folder="./dist/Equicord/dist/browser"
else
    source_folder="./dist/Vencord/dist"
fi

cp -f "$source_folder/browser.js" "$destination_folder/bundle.js"
cp -f "$source_folder/browser.css" "$destination_folder/bundle.css"
