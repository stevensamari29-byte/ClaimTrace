# Nightshift Windows activation evidence — October 25, 2026

Independent native inspection by `nightshift_activation`, continuing PR #11 on `codex/live-nemotron`. No Nightshift installation, model download, inference, key-store modification, service startup or Git mutation was performed by this inspection. Direct NVIDIA hosted inference is a separate integration and does not establish Nightshift usage.

## Actual local observations

| Check | Observed result |
| --- | --- |
| OS | Windows 11 Home, 64-bit, version `10.0.26300`. |
| CPU | Intel Core i5-1135G7, 4 cores / 8 logical processors. |
| Memory | 7.79 GiB visible RAM; approximately 0.91 GiB free at the inspection instant. Free memory changes during use. |
| GPU | Intel Iris Xe integrated graphics. No dedicated GPU appeared in the `Win32_VideoController` inventory. Its reported adapter-memory value is not a reliable measure of usable shared graphics memory. |
| Download | `Nightshift-Setup-Windows.exe`, 660,155,436 bytes, in the existing Downloads directory. |
| Installed application | `%LOCALAPPDATA%\Nightshift\meterless-runtime.exe`, product Nightshift, version `1.2.7`. Existing `meterlessd.exe`, engine files, CLI and bundled Node are present. Installation is therefore established; readiness is separate. |
| CLI | `%LOCALAPPDATA%\Nightshift\cli\ns.cmd` invokes the installed `node\node.exe` and `cli\ns.mjs`. No installer or downloader is invoked by this wrapper. |
| Process/listener | No `meterless-runtime`, `meterlessd`, Nightshift or `llama-server` process was observed; no listener was observed on loopback port 8088. |

Commands used for hardware inventory were bounded `Get-CimInstance Win32_Processor`, `Win32_OperatingSystem` and `Win32_VideoController` projections. No serial numbers, device identifiers, unrelated applications or personal files were collected.

## Installer provenance

The downloaded installer's SHA-256 is:

```text
3e7e2f2e49adc29ba4bd1c76263bf94aa684dc42b3381e331cce060e5f4ec677
```

It exactly matches the current entry returned by the official HTTPS [SHA256SUMS](https://meterless.ai/Nightshift/WIN/SHA256SUMS). The download's Windows origin metadata names `https://meterless.ai/windows.html` and the official `/Nightshift/WIN/Nightshift-Setup-Windows.exe` path. No full installer redownload was needed.

`Get-AuthenticodeSignature` reports the installer and Nightshift runtime as `NotSigned`; bundled Node `22.23.2` has a valid OpenJS Foundation signature. The official [build-information file](https://meterless.ai/Nightshift/WIN/APP_BUILD_INFO.txt) also describes an unsigned development artifact, but its cached version referred to an older release. The web search/text cache initially returned an older SHA list; a direct bounded HTTPS fetch of the current checksum file resolved the mismatch. Unsigned does not mean the runtime was verified safe or compatible; the exact official installer hash establishes the observed download's provenance.

## Actual CLI readiness tests

After checking the wrapper, installed transport source and official provenance, these read-only commands were run against the installed CLI:

```powershell
& "$env:LOCALAPPDATA\Nightshift\cli\ns.cmd" status --json --timeout 2000
& "$env:LOCALAPPDATA\Nightshift\cli\ns.cmd" discover --json --timeout 2000
```

Both returned **exit 12**, `ok: false`, error code **`E_UNREACHABLE`**. Commands were captured with a 22-second parent process bound and only whitelisted result fields were printed. No runtime token or provider credential was printed. Neither command starts the daemon or loads a model. The [official CLI reference](https://meterless.ai/cli.html) defines these as read operations, identifies exit 12 as unreachable, and documents the default loopback endpoint and runtime-owned token. It explicitly excludes provider-key, model and lane administration from the CLI.

**Result:** a working local Nightshift endpoint at `http://127.0.0.1:8088/v1` has not been demonstrated. Neither `/v1/models` routing IDs nor a native structured tool response have been obtained from this Runtime.

## Hardware and hosted-provider compatibility

The current [Windows page](https://meterless.ai/windows.html) and official [edition requirements](https://raw.githubusercontent.com/Meterless/Meterless/main/docs/products/nightshift/editions.md) specify a dedicated GPU for the Windows local-model edition. This laptop does not match that advertised hardware configuration. Do not infer that a local GPU fleet is supported merely because the installer ran. No local LLM was downloaded or started.

Hosted NVIDIA routing is present in the installed official software, independently of this hardware limitation:

- Installed `engine/js/engine/providers.js` implements a NVIDIA provider using `https://integrate.api.nvidia.com/v1`, passes native `tools`/`tool_choice`, and uses the runtime's existing private provider-key interface. This is inspected implementation, not a successful hosted request.
- Installed `engine/js/engine/models.js` contains hosted NVIDIA Nemotron rows. The `nvidia/nemotron-3.5-lightning-30b-a3b` row advertises native tools. The old `nvidia/nemotron-3-super-120b-a12b` row is gated off by default with an account-unavailable note. These are the vendor's source annotations, not proof of this user's account entitlement or model availability.
- The official downloadable [manifest](https://meterless.ai/Nightshift/WIN/manifest.json) describes a NVIDIA provider entry and encrypted local key storage. It also contains default-prefetch local model entries, so rerunning setup is not an appropriate cloud-only activation step.
- Official [hotspot documentation](https://raw.githubusercontent.com/Meterless/Meterless/main/docs/products/nightshift/hotspot.md) describes the authenticated OpenAI-compatible interface. `meterless/*` names are routing modes, not underlying model identity. The free web edition does not supply the same local hotspot.

A supported **cloud-only Windows startup on this integrated-GPU laptop remains unverified**. The existing app was not launched during this inspection: its cold-start path could not be shown to avoid automatic local lane loading/downloads, and the brief explicitly prohibits local large-model execution. This is an unverified startup configuration, not proof that the executable cannot start. No setting was changed to conceal or bypass hardware requirements.

## Smallest next steps

1. Continue the directly authorized hosted NVIDIA test in ClaimTrace, separately labelled from Nightshift. Use a currently available account-authorized model; the old model's presence in documentation alone is insufficient.
2. Establish from the existing app's supported setup controls or Meterless support whether this Windows edition can start with **no local models and cloud-only routing**. Do not rerun the large installer or accept default model downloads. If this cannot be established, use an already-authorized supported host rather than forcing a local fleet onto this laptop.
3. If supported, the eligible owner privately enters the NVIDIA key through Nightshift's supported provider-key UI. Do not copy the key into command arguments, chat, source files, logs or ClaimTrace reports. The CLI is not a key-configuration mechanism.
4. With a running daemon, rerun status/discover, then authenticated `/v1/models` through the preserved ClaimTrace client. Verify native structured tool calls and the underlying Nemotron identity before claiming the combined integration.
5. Retain a redacted actual completion/tool receipt and bounded financial investigation. A healthy process, installed files, provider source code or routing IDs alone are insufficient.

No organizer/support message was sent, and no alternative cloud Nightshift endpoint was invented. The contact and supported host decision remain human/sponsor dependencies if the cloud-only startup path is unavailable.

## October 26 — final bounded compliance-critical attempt

The lead directed one final technically supported attempt because actual Nightshift provider execution is a mandatory organizer requirement. This section supersedes any suggestion that direct NVIDIA calls or H-MEM alone complete that requirement. No NVIDIA key was read, copied, printed or passed by this reviewer.

Rechecked the existing installed normal launcher: the Start Menu `Nightshift.lnk` targets `meterless-runtime.exe` **with no arguments**, and the installed product remains version `1.2.7`. No cloud-only/no-local-model startup flag is configured on that launcher. Official [Windows requirements](https://meterless.ai/windows.html), [edition documentation](https://raw.githubusercontent.com/Meterless/Meterless/main/docs/products/nightshift/editions.md) and [CLI reference](https://meterless.ai/cli.html) were rechecked; they did not establish a supported no-local-model boot control for this integrated-GPU Windows machine. The previously inspected official manifest includes default-prefetch local models. This is a specific missing safe startup control, not a claim that the application can never run.

One readiness attempt executed the two documented read commands, each once, with the same 2-second request timeout and 22-second parent bound:

| Command | Actual child exit | Sanitized result |
| --- | --- | --- |
| `ns.cmd status --json --timeout 2000` | 12 | `ok: false`, `E_UNREACHABLE` |
| `ns.cmd discover --json --timeout 2000` | 12 | `ok: false`, `E_UNREACHABLE` |

No existing Nightshift/daemon/local-model process or loopback 8088 listener was observed in the preflight. No daemon was started, no inference was issued and no local model was downloaded or loaded. The ordinary GUI launcher was not executed because its lack of a verified cloud-only startup control leaves local lane autoload/prefetch unresolved, while the authorized attempt explicitly prohibits local model execution and unsupported flags. The dedicated-GPU requirement remains unmet. Replacing the daemon with an ad-hoc backend, inventing a cloud edition or bypassing its checks would not be a genuine supported Nightshift integration.

**Final status: blocked, actual Nightshift AI-provider execution not demonstrated.** The bounded attempt is complete; do not silently substitute direct NVIDIA inference or the working H-MEM engine for this requirement.

**Exact human/sponsor dependency:** obtain Meterless confirmation/instructions for starting the already-installed Windows 1.2.7 runtime in a supported cloud-only mode on Intel Iris Xe with 8 GB RAM, with all local-model autoload/downloads disabled; alternatively provide an already-authorized compatible Nightshift host. If a supported startup is confirmed, the owner/root must use Nightshift's official NVIDIA provider-key settings to enter the existing key privately (the `ns` CLI does not administer keys), enable an authorized hosted Nemotron route, and let ClaimTrace verify real authenticated model discovery plus a bounded native tool-call investigation. The current provider-settings field/flow was not inspected in a running GUI, so no unobserved button sequence is represented as verified. No support message, key-store modification, new installation, spending or external host creation was performed.
