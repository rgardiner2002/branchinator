# Network Provisioning Planner

Open index.html in Chrome, Edge or Firefox. No server, installation or internet connection is needed. All calculations run locally in JavaScript (Python ipaddress would require a backend or embedded Python runtime).

## Workflow
1. Enter a site/scope name and CI prefix, plus core/access switch counts.
2. Add VLAN subnet rows (DEVICE MGMT, DATA, WIRELESS, VOIP). Use network addresses, not host IPs. One subnet per type is supported per site. Select the DEVICE MGMT subnet for switches.
3. Build device rows, then enter each switch's actual serial and colon-separated MAC address.
4. Calculate and review. Download DHCP CSV and switch variables CSV separately.

Core switches receive addresses first, followed by access switches. Each naming role starts at 01; one shared IP sequence starts at gateway + 1. Hostnames: {CI Prefix}-coresw01 and {CI Prefix}-accsw01. A two-digit minimum means switch 100 uses 100, not a truncated value.

Gateway = network + 1. /24 DHCP pool = network + 100 through network + 250. Other supported prefixes (/1 to /30) use gateway + 1 through broadcast - 1. /31 and /32 are rejected. Host bits and overlapping VLAN subnets are rejected. One DEVICE MGMT subnet serves all switches.

IMPORTANT: For non-/24 management networks the proposed DHCP pool overlaps the statically assigned switch addresses. The page warns but retains the original requested pool. Configure DHCP exclusions/reservations for switches, disable DHCP on DEVICE MGMT, or revise the address plan before deployment. Existing live allocations cannot be discovered by an offline page. This is a planning/export tool, not deployment automation.

Variables CSV columns exactly match the supplied example, including case and order:
_sys_serial,_sys_lan_mac,modified,_sys_default_gateway,_sys_hostname,_SYS_DATA_IP

Every row has modified=Y. IPs include /prefix; gateway does not. UTF-8 without BOM, CRLF line endings, CSV quoting where needed. Blank or duplicate device identities block variables download but not a valid DHCP-only download. Changing the form disables stale downloads until recalculated. Changing switch counts/names/management subnet requires rebuilding device rows. Serial/MAC values are retained by hostname during rebuilds. Form inputs and device rows are stored in the URL fragment as you edit them. Reloading or opening a copied configuration link restores the saved inputs. Recalculate to regenerate the review and CSV exports. No database or telemetry is used.

DHCP CSV columns:
scope_name,vlan_type,subnet,subnet_mask,network_address,broadcast_address,default_gateway,pool_start,pool_end

## Share a configuration

Use the small **Copy config link** button at the top-left of the header, or copy the URL from the address bar. New links use compact, compressed URL-safe encoding; older configuration links remain supported. Opening the link restores the site name, CI prefix, switch counts, VLANs, management selection and device rows. The URL fragment is not sent to the web server, but it is not encrypted and can be retained in browser history or copied by recipients. Share only with trusted recipients; large configurations may still exceed some apps’ URL length limits. A fixed-length short link would require external storage; the current implementation remains fully browser-only. Offline file links only work for recipients who have the file at the corresponding path; use the hosted GitHub Pages URL for sharing between machines.

## Publish with GitHub Pages

1. Create or open the GitHub repository you want to use (for example, `network-planner`). A public repository is the simplest option; private-repository Pages availability depends on your GitHub plan.
2. Extract the GitHub Pages ZIP locally. Upload **the contents of its folder**, including `index.html`, `README.md` and `.nojekyll`, to the root of the repository's `main` branch. Do not upload the ZIP itself or nest index.html inside another folder. The test script and example CSV are optional; the webpage needs only index.html and .nojekyll.
3. Open repository **Settings → Pages**.
4. Under **Build and deployment**, set **Source → Deploy from a branch**.
5. Select branch **main**, folder **/ (root)**, then click **Save**.
6. Wait for GitHub's Pages deployment to finish. The Pages settings screen will show the published URL, normally `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/`.
7. Open the site, complete the form and download the CSV files. Subsequent commits to main redeploy the page.

No npm build, Python server, GitHub Actions workflow, API token or environment secrets are needed. `.nojekyll` keeps this a plain static deployment. Everything is inline in index.html, with no absolute asset paths, so repository subpaths work. The same file still opens offline.

### Privacy and visibility
GitHub Pages is a hosted site; do not assume a private repository makes its published site private. Do not commit actual device serials, MAC addresses, network exports, credentials or production data. Visitors enter device details in their own browser; this app stores their form values in the URL fragment, not on a server. Anyone with that link can read the included values. GitHub receives ordinary requests for the webpage. Downloads are generated in the browser. There is no login or server-side access control in this application.

## Verification
The included test_planner.py uses Playwright Chromium and Python ipaddress. Run with:
  pip install playwright
  python -m playwright install chromium
  python test_planner.py
The supplied example.csv is included for the exact-header comparison. Tests also cover URL round-trip restoration, reloads, URL-safe characters, removing VLANs and malformed links.

Verified offline file:// browser operation, exact example CSV header and CRLF, actual downloads, seven subnet calculations compared with Python ipaddress, invalid subnet rejection, seven-device naming/allocation, duplicate identities, form invalidation, identity preservation, subnet overlap, DHCP-only exports, mobile layout and zero page JavaScript errors.
