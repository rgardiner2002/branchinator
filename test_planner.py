from playwright.sync_api import sync_playwright
import csv, io, ipaddress, pathlib, json, os
ROOT=pathlib.Path(__file__).parent
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100},accept_downloads=True)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(os.environ.get('PLANNER_TEST_URL', (ROOT/'index.html').as_uri()))
    # Actual JS calculations cross-checked against Python standard library.
    for cidr in ['192.168.10.0/24','192.168.10.64/26','192.168.10.96/27','192.168.10.128/28','10.0.0.0/16','128.0.0.0/1','192.168.10.0/30']:
        result=page.evaluate('(c)=>subnet(c)',cidr)
        net=ipaddress.ip_network(cidr)
        assert result['broadcast']==int(net.broadcast_address)
        assert result['net']==int(net.network_address)
        assert result['mask']==str(net.netmask)
        assert result['start']==int(net.network_address)+(100 if net.prefixlen==24 else 2)
        assert result['end']==(int(net.network_address)+250 if net.prefixlen==24 else int(net.broadcast_address)-1)
    for invalid in ['192.168.10.80/26','256.0.0.0/24','10.0.0.0/31','1.2.3.4','1.2.3.4/32']:
        assert page.evaluate('(c)=>{try{subnet(c);return false}catch(e){return true}}',invalid)
    page.locator('#site').fill('Dudley Office')
    page.locator('#prefix').fill('uk-du')
    page.locator('#core').fill('2')
    page.locator('#access').fill('5')
    page.locator('[data-field=cidr]').fill('192.168.10.64/27')
    page.locator('#add').click()
    page.locator('[data-field=cidr]').nth(1).fill('192.168.20.0/24')
    page.locator('#build').click()
    rows=page.locator('#devices tr')
    assert rows.count()==7
    assert rows.nth(0).locator('td').nth(0).inner_text()=='uk-du-coresw01'
    assert rows.nth(2).locator('td').nth(0).inner_text()=='uk-du-accsw01'
    assert rows.nth(6).locator('td').nth(0).inner_text()=='uk-du-accsw05'
    for i in range(7):
        rows.nth(i).locator('input').nth(0).fill(f'SERIAL{i+1}')
        rows.nth(i).locator('input').nth(1).fill(f'00:11:22:33:44:{i+1:02x}')
    page.get_by_role('button',name='Calculate & review').click()
    assert page.locator('#varsDownload').is_enabled()
    assert 'DHCP overlap' in page.locator('#status').inner_text()
    for button,filename in [('varsDownload','tested-switch-variables.csv'),('dhcpDownload','tested-dhcp-scopes.csv')]:
        with page.expect_download() as info:page.locator('#'+button).click()
        info.value.save_as(ROOT/filename)
    data=(ROOT/'tested-switch-variables.csv').read_bytes()
    assert b'\r\n' in data
    records=list(csv.reader(io.StringIO(data.decode())))
    example=(ROOT/'example.csv').read_text().splitlines()[0]
    assert ','.join(records[0])==example
    assert records[1]==['SERIAL1','00:11:22:33:44:01','Y','192.168.10.65','uk-du-coresw01','192.168.10.66/27']
    assert records[-1][-1]=='192.168.10.72/27'
    assert len(records)==8
    dhcp=list(csv.DictReader(io.StringIO((ROOT/'tested-dhcp-scopes.csv').read_text())))
    assert dhcp[0]['pool_end']=='192.168.10.94'
    assert dhcp[1]['pool_start']=='192.168.20.100' and dhcp[1]['pool_end']=='192.168.20.250'
    page.screenshot(path=str(ROOT/'preview.png'),full_page=True)
    # Dirty edits disable exports, rebuilding preserves entered identities.
    rows.nth(0).locator('input').nth(0).fill('UPDATED1')
    assert page.locator('#varsDownload').is_disabled()
    page.locator('#build').click()
    assert rows.nth(0).locator('input').nth(0).input_value()=='UPDATED1'
    # Duplicate serial validation.
    rows.nth(1).locator('input').nth(0).fill('UPDATED1')
    page.get_by_role('button',name='Calculate & review').click()
    assert page.locator('#varsDownload').is_disabled()
    assert 'Duplicate serial' in page.locator('#status').inner_text()
    assert page.locator('#dhcpDownload').is_enabled()
    # Overlap blocks both exports.
    page.locator('[data-field=cidr]').nth(1).fill('192.168.10.0/24')
    page.get_by_role('button',name='Calculate & review').click()
    assert 'overlap' in page.locator('#status').inner_text()
    assert page.locator('#dhcpDownload').is_disabled()
    # DHCP-only operation, no device identities required.
    page.locator('[data-field=cidr]').nth(1).fill('192.168.20.0/24')
    page.locator('#core').fill('0');page.locator('#access').fill('0')
    page.get_by_role('button',name='Calculate & review').click()
    assert page.locator('#dhcpDownload').is_enabled() and page.locator('#varsDownload').is_disabled()
    # Mobile layout contained in viewport (tables scroll internally).
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not errors, errors
    print(json.dumps({'result':'PASS','subnet_cases':7,'invalid_subnets':5,'exported_switches':7,'exact_example_header':True,'CRLF':True,'download_tests':2,'browser_errors':errors,'checks':['core/access zero padding','shared IP sequence','CIDR preservation','DHCP /24 special range','overlap warnings','dirty export invalidation','identity preservation','duplicate identity blocking','subnet overlap blocking','DHCP only','mobile width','hosted project URL' if os.environ.get('PLANNER_TEST_URL') else 'offline file URL']},indent=2))
    browser.close()
