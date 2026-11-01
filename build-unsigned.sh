#!/bin/bash
set -euo pipefail
test "$(uname -s)" = Darwin || { echo 'Xcode/macOS build host required'; exit 1; }
test -d /Applications/Xcode_26.6.app || { echo 'Audited Xcode 26.6 missing; stop'; exit 1; }
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
kit_dir="$(cd "$(dirname "$0")" && pwd)"
input_dir="${1:?prepared source directory required}"
output_dir="${2:?new output directory required}"
test ! -e "$output_dir" || { echo 'Output exists; stop'; exit 1; }
mkdir -p "$output_dir"
xcodebuild -version > "$output_dir/build-environment.txt"
xcodebuild -project "$input_dir/app/apps/ios/PhoneUseRemoteOnly.xcodeproj" \
  -scheme IPhoneUseRemote -configuration Release -sdk iphoneos \
  -destination 'generic/platform=iOS' -derivedDataPath "$output_dir/derived" \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY= \
  IPU_APP_BUNDLE_ID=local.owner.browsertrial DEVELOPMENT_TEAM= \
  build > "$output_dir/build.log" 2>&1
app="$output_dir/derived/Build/Products/Release-iphoneos/Phone Use Remote.app"
test -d "$app"
mkdir "$output_dir/Payload"
ditto "$app" "$output_dir/Payload/Phone Use Remote.app"
python3 "$kit_dir/verify-package.py" "$output_dir/Payload/Phone Use Remote.app"
(cd "$output_dir" && /usr/bin/zip -qr browser-trial-UNSIGNED.ipa Payload)
(cd "$output_dir" && shasum -a 256 browser-trial-UNSIGNED.ipa > browser-trial-UNSIGNED.ipa.sha256)
echo 'Unsigned build only. Not installed. A valid owner-signing path is still required.'
