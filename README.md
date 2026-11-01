# Unsigned browser evaluation build

A build recipe for evaluating the remote-only browser from leeguooooo/iphone-use v0.27.31, with a locked public archive and a small validation-only safety overlay. The upstream PolyForm Shield license remains applicable; see UPSTREAM-LICENSE.txt.

This is not a released iOS app or an AI-success claim. The initial build disables browser-model networking, automatic clicks, selections, arbitrary site scripts and profile filling. A clearly labelled deterministic LOCAL_FIXTURE checks dummy input and scrolling; it is not an AI model.

Manually dispatched only, standard macos-26 runner, public repositories only. No Apple credentials, signing identities or device data are supplied. No Actions cache or artifacts. An unsigned IPA is retained in an owner-only draft release. It cannot be installed without a separately authorized valid signing process.

After installation, local-test in the browser address opens the embedded synthetic fixture. LOCAL_FIXTURE is the mock acceptance goal. Device installation, actual free inference, iOS runtime behavior and standalone use remain unverified until separately tested.

Local DOM tests require Node and an already installed jsdom: set TEST_DEPENDENCY_OWNER and PREPARED_SOURCE, then run node --test test-dom.mjs. They test the real embedded JavaScript extracted from the prepared Swift source, not a simulator.
