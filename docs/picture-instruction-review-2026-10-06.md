# Picture instruction audit — October 6, 2026

The shared catalogue now has **46 routes and 403 numbered illustrations**. The one additional route is for a newer VIZIO TV that shows **My Hub → Connect your Walmart account**. The existing **Extras → VIZIO Account** route remains limited to TVs that actually show that older menu. These are TV and phone instructions within the official products; completing them does not establish an Audio Bodyguard connection.

## Pass 1 — completeness and cross-references

Every route is reachable from a group, and every source is used by a route. All 403 steps have a surface, screen label, action, one valid focus target, instruction, optional note, and one numbered picture in the offline companion. The generated Swift and Kotlin catalogues match the JSON source. The offline HTML's number, surface, instruction, accessible picture label and visible highlight were checked for every step; none are absent or clipped beyond the two rendered lines. iPhone installation steps use App Store/Get; Android installation steps use Google Play/Install. Phone Wi-Fi steps remain separate for iPhone, Pixel and Galaxy. TV, Google Home and Alexa routes remain distinct.

## Pass 2 — chronology and image matching

Roku's **model** route says **Home → Settings → System → About**. Its third image incorrectly highlighted **Network** because the renderer inferred the route from a generic `Roku • Settings` screen caption. The iOS, Android and offline renderers now use the route identity, so the model picture shows System and the IP-address route still shows Network. Roku's current support instructions corroborate [System → About for the model](https://support.roku.com/en-us/article/how-to-know-if-you-have-a-roku-tv) and [Network → About for network information](https://support.roku.com/article/check-your-network-connection).

VIZIO's current documentation describes two account flows. A newer TV that displays My Hub uses the TV's Walmart-account QR path before pairing the phone with VIZIO Mobile's separate four-digit code. The new 14-picture route follows that order. A TV displaying Extras → VIZIO Account retains the separate six-digit account-code route. The phone-pairing route now follows whichever account the official app asks for. These distinctions come from [VIZIO's newer account guide](https://www.vizio.com/en/overview-account), [VIZIO Mobile pairing](https://www.vizio.com/en/mobile), and the [older account-code guide](https://www.vizio.com/en/vizio-account/link-your-tv).

## Pass 3 — source and label accuracy

The old VIZIO Mobile URL redirected away from VIZIO; the catalogue now links to the current official Mobile page. VIZIO's Google Home and Alexa guides point to their corresponding VIZIO sources. The Alexa route no longer cites Google's provider-linking article. Where VIZIO does not publish an exact partner button label, the picture uses a descriptive **Google Home option** or **Amazon Alexa option** and tells the user to follow the official app. The unused Google hub source was removed. Official phone and TV support pages were checked again for the other existing route families; the step catalogue keeps platform, model and region qualifications.

These pictures are **labeled instructional schematics**. They are not verified photographs of each TV model, firmware, country, or current app build. The model/mismatch action and source links remain available when the actual screen differs. Hardware testing with the exact devices is required before claiming photograph-level fidelity or successful physical pairing.

The focused Roku highlight and VIZIO account-path regressions were first reproduced as failures, then passed after correction. Generator parity, 403 offline picture matches, shell syntax and diff whitespace checks pass locally. Native simulator and emulator results are recorded in draft PR #32 for the delivered commit.
