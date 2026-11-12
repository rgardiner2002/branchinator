# Network Provisioning Planner

Open index.html in Chrome, Edge or Firefox. No server, installation or internet connection is needed. All calculations run locally in JavaScript (Python ipaddress would require a backend or embedded Python runtime).

## Workflow
1. Enter a site/scope name and CI prefix, plus core/access switch counts.
2. Add VLAN subnet rows (DEVICE MGMT, DATA, WIRELESS, VOIP). Use network addresses, not host IPs. One subnet per type is supported per site. Select the DEVICE MGMT subnet for switches.
3. Build device rows, then enter each switch's actual serial and colon-separated MAC address. Optionally click **+ Add parameter** to append custom columns to the variables CSV. Give each parameter a field name and an optional default value; override values in individual device rows as needed.
4. Calculate and review. Download DHCP CSV and switch variables CSV separately.

Core switches receive addresses first, followed by access switches. Each naming role starts at 01; one shared IP sequence starts at gateway + 1. Hostnames: {CI Prefix}-coresw01 and {CI Prefix}-accsw01. A two-digit minimum means switch 100 uses 100, not a truncated value.

Gateway = network + 1. /24 DHCP pool = network + 100 through network + 250. Other supported prefixes (/1 to /30) use gateway + 1 through broadcast - 1. /31 and /32 are rejected. Host bits and overlapping VLAN subnets are rejected. One DEVICE MGMT subnet serves all switches. DATA, WIRELESS and VOIP have individual start/end sliders and exact numeric offset fields, with a live address preview and Reset range. Defaults remain +100 to +250 for /24 and +2 to the last usable address for other supported prefixes. Custom ranges are saved in shared configuration links and used in CSV and formatted clipboard exports. The management pool remains automatic.

Management DHCP starts at the greater of the normal pool start and the first address after the last assigned switch IP (gateway + total switch count + 1). This reserves planned switch addresses without changing other VLAN pools. If no addresses remain in the permitted pool, DHCP export is blocked, but valid switch variables can still be exported. Existing live allocations cannot be discovered by an offline page. This is a planning/export tool, not deployment automation.

The variables CSV always starts with the original six columns, including case and order:
_sys_serial,_sys_lan_mac,modified,_sys_default_gateway,_sys_hostname,_SYS_DATA_IP

Any custom parameter names are appended as extra columns after these six. Parameter names must be unique (case-insensitive), must not duplicate a built-in header, and must begin with a letter or underscore. They may contain letters, numbers, underscores, dots and hyphens. Each parameter can have a default value for all switches plus per-device overrides; blank values are allowed. Up to 20 custom columns are supported. Without custom parameters, the original six-column CSV is unchanged. Custom columns and per-device overrides are saved in configuration URLs, including compact share links.

Every row has modified=Y. MAC addresses are output in lowercase regardless of input case. IPs include /prefix; gateway does not. UTF-8 without BOM, CRLF line endings, CSV quoting where needed. Blank or duplicate device identities block variables download but not a valid DHCP-only download. Changing the form disables stale downloads until recalculated. Changing switch counts/names/management subnet requires rebuilding device rows. Serial/MAC values are retained by hostname during rebuilds. Form inputs and device rows are stored in the URL fragment as you edit them. Reloading or opening a copied configuration link restores the saved inputs. Recalculate to regenerate the review and CSV exports. No database or telemetry is used.

DHCP CSV columns:
scope_name,vlan_type,subnet,subnet_mask,network_address,broadcast_address,default_gateway,pool_start,pool_end

## Share a configuration

Use the small **Copy config link** button at the top-right above the header, or copy the URL from the address bar. New links use compact, compressed URL-safe encoding; older configuration links remain supported. Opening the link restores the site name, CI prefix, switch counts, VLANs, management selection, device rows and custom variable parameters. The URL fragment is not sent to the web server, but it is not encrypted and can be retained in browser history or copied by recipients. Share only with trusted recipients; large configurations may still exceed some apps’ URL length limits. A fixed-length short link would require external storage; the current implementation remains fully browser-only. Offline file links only work for recipients who have the file at the corresponding path; use the hosted GitHub Pages URL for sharing between machines.

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

Verified offline file:// browser operation, exact example CSV header and CRLF, actual downloads, seven subnet calculations compared with Python ipaddress, invalid subnet rejection, seven-device naming/allocation, duplicate identities, form invalidation, identity preservation, management DHCP switch exclusions, subnet overlap, DHCP-only exports, mobile layout and zero page JavaScript errors.
