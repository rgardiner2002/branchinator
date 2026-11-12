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
    page.locator('#site').fill('Example Office')
    page.locator('#prefix').fill('uk-xx')
    page.locator('#core').fill('2')
    page.locator('#access').fill('5')
    page.locator('[data-field=cidr]').fill('192.168.10.64/27')
    page.locator('#add').click()
    page.locator('[data-field=cidr]').nth(1).fill('192.168.20.0/24')
    page.locator('#build').click()
    rows=page.locator('#devices tr')
    assert rows.count()==7
    assert rows.nth(0).locator('td').nth(0).inner_text()=='uk-xx-coresw01'
    assert rows.nth(2).locator('td').nth(0).inner_text()=='uk-xx-accsw01'
    assert rows.nth(6).locator('td').nth(0).inner_text()=='uk-xx-accsw05'
    for i in range(7):
        rows.nth(i).locator('input').nth(0).fill(f'SERIAL{i+1}')
        rows.nth(i).locator('input').nth(1).fill(f'00:11:22:33:44:{i+1:02x}')
    rows.nth(1).locator('input').nth(1).fill('AA:BB:CC:DD:EE:FF')
    page.get_by_role('button',name='Calculate & review').click()
    assert page.locator('#varsDownload').is_enabled()
    assert 'Management DHCP starts at 192.168.10.73' in page.locator('#status').inner_text()
    # Formatted DHCP scope text uses the calculated (switch-safe) pool.
    expected_text = (
        'Device Management:\nExample Office - DEVICE MGMT\n'
        '          IPv4 network: 192.168.10.64/27\n'
        '          Address Pool: 192.168.10.73 - 192.168.10.94\n'
        '          Router IP: 192.168.10.65/27\n\n'
        'Data:\nExample Office - DATA\n'
        '          IPv4 network: 192.168.20.0/24\n'
        '          Address Pool: 192.168.20.100 - 250\n'
        '          Router IP: 192.168.20.1'
    )
    assert page.evaluate('dhcpText(review.dhcp)') == expected_text
    page.evaluate("Object.defineProperty(navigator, 'clipboard', {configurable:true,value:{writeText:async text=>{window.copiedScopes=text;}}})")
    page.locator('#copyDhcp').click()
    page.wait_for_function("document.getElementById('dhcpCopyStatus').textContent === 'Copied!'")
    assert page.evaluate('window.copiedScopes') == expected_text

    for button,filename in [('varsDownload','tested-switch-variables.csv'),('dhcpDownload','tested-dhcp-scopes.csv')]:
        with page.expect_download() as info:page.locator('#'+button).click()
        info.value.save_as(ROOT/filename)
    # Individual switch exports contain only that device and retain the exact CSV schema.
    assert page.locator('.device-file').count()==7
    assert page.get_by_role('button',name='Download variables CSV for uk-xx-coresw01').count()==1
    for name,serial,mac,ip in [
        ('uk-xx-coresw01','SERIAL1','00:11:22:33:44:01','192.168.10.66/27'),
        ('uk-xx-coresw02','SERIAL2','aa:bb:cc:dd:ee:ff','192.168.10.67/27'),
        ('uk-xx-accsw05','SERIAL7','00:11:22:33:44:07','192.168.10.72/27'),
    ]:
        with page.expect_download() as info:
            page.get_by_role('button',name='Download variables CSV for '+name).click()
        assert info.value.suggested_filename==name+'-variables.csv'
        target=ROOT/('tested-'+name+'-variables.csv')
        info.value.save_as(target)
        raw=target.read_bytes()
        assert b'\r\n' in raw
        csv_rows=list(csv.reader(io.StringIO(raw.decode('utf-8'))))
        assert len(csv_rows)==2
        assert csv_rows[0]==(ROOT/'example.csv').read_text().splitlines()[0].split(',')
        assert csv_rows[1]==[serial,mac,'Y','192.168.10.65',name,ip]
    data=(ROOT/'tested-switch-variables.csv').read_bytes()
    assert b'\r\n' in data
    records=list(csv.reader(io.StringIO(data.decode())))
    example=(ROOT/'example.csv').read_text().splitlines()[0]
    assert ','.join(records[0])==example
    assert records[1]==['SERIAL1','00:11:22:33:44:01','Y','192.168.10.65','uk-xx-coresw01','192.168.10.66/27']
    assert records[2][1]=='aa:bb:cc:dd:ee:ff'
    assert records[-1][-1]=='192.168.10.72/27'
    assert len(records)==8
    dhcp=list(csv.DictReader(io.StringIO((ROOT/'tested-dhcp-scopes.csv').read_text())))
    assert dhcp[0]['pool_start']=='192.168.10.73' and dhcp[0]['pool_end']=='192.168.10.94'
    assert dhcp[1]['pool_start']=='192.168.20.100' and dhcp[1]['pool_end']=='192.168.20.250'
    page.screenshot(path=str(ROOT/'preview.png'),full_page=True)
    # Shareable URL round-trip: restore a complete configuration in a fresh tab.
    shared_url=page.url
    assert '#cfg=2' in shared_url
    legacy_payload=page.evaluate('encodeURIComponent(JSON.stringify(snapshot()))')
    assert len(shared_url.split('#cfg=')[1]) < len(legacy_payload)
    shared=browser.new_page(viewport={'width':1440,'height':1100},accept_downloads=True)
    shared.on('pageerror',lambda e:errors.append(str(e)))
    shared.goto(shared_url)
    assert shared.locator('#site').input_value()=='Example Office'
    assert shared.locator('#prefix').input_value()=='uk-xx'
    assert shared.locator('#core').input_value()=='2'
    assert shared.locator('#access').input_value()=='5'
    assert shared.locator('[data-field=cidr]').nth(0).input_value()=='192.168.10.64/27'
    assert shared.locator('[data-field=cidr]').nth(1).input_value()=='192.168.20.0/24'
    assert shared.locator('input[name=mgmt]').nth(0).is_checked()
    assert shared.locator('#devices tr').count()==7
    assert shared.locator('#devices tr').nth(0).locator('input').nth(0).input_value()=='SERIAL1'
    assert shared.locator('#devices tr').nth(6).locator('input').nth(1).input_value()=='00:11:22:33:44:07'
    assert shared.locator('#devices tr').nth(1).locator('input').nth(1).input_value()=='AA:BB:CC:DD:EE:FF'
    shared.get_by_role('button',name='Calculate & review').click()
    assert shared.locator('#varsDownload').is_enabled()
    shared.locator('#site').fill('A & B / 100%')
    updated_url=shared.url
    assert updated_url!=shared_url
    shared.reload()
    assert shared.locator('#site').input_value()=='A & B / 100%'
    assert shared.locator('#devices tr').count()==7
    shared.locator('#scopes tr').nth(1).get_by_role('button',name='Remove').click()
    shared.reload()
    assert shared.locator('#scopes tr').count()==1
    shared.goto(shared_url.split('#')[0]+'#cfg=%7Bbad')
    assert 'invalid or unsupported' in shared.locator('#shareStatus').inner_text()
    shared.goto(shared_url.split('#')[0]+'#cfg='+legacy_payload)
    assert shared.locator('#site').input_value()=='Example Office'
    assert shared.locator('#devices tr').count()==7
    assert shared.locator('#devices tr').nth(0).locator('input').nth(0).input_value()=='SERIAL1'
    shared.close()
    # Dirty edits disable exports, rebuilding preserves entered identities.
    rows.nth(0).locator('input').nth(0).fill('UPDATED1')
    assert page.locator('#varsDownload').is_disabled()
    assert page.locator('.device-file').count()==0
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
    # Management /24 preserves the normal +100 floor.
    page.locator('[data-field=cidr]').nth(0).fill('192.168.10.0/24')
    page.locator('#core').fill('2')
    page.get_by_role('button',name='Calculate & review').click()
    assert page.evaluate('review.dhcp[0][7]')=='192.168.10.100'
    # Moving past +100 when switches occupy that range.
    page.locator('#core').fill('100')
    page.get_by_role('button',name='Calculate & review').click()
    assert page.evaluate('review.dhcp[0][7]')=='192.168.10.102'
    # A /30 with one switch leaves no DHCP pool, but switch export still works.
    page.locator('[data-field=cidr]').nth(0).fill('192.168.10.64/30')
    page.locator('#core').fill('1')
    page.locator('#build').click()
    rows.nth(0).locator('input').nth(0).fill('TEST1')
    rows.nth(0).locator('input').nth(1).fill('00:11:22:33:44:01')
    page.get_by_role('button',name='Calculate & review').click()
    assert 'no DHCP addresses remain' in page.locator('#status').inner_text()
    assert page.locator('#dhcpDownload').is_disabled()
    assert page.locator('#varsDownload').is_enabled()
    # Custom DHCP pools: independent ranges, URL persistence, and reset.
    custom=browser.new_page(viewport={'width':1440,'height':1100})
    custom.on('pageerror',lambda e:errors.append(str(e)))
    custom.goto(shared_url.split('#')[0])
    custom.locator('#site').fill('Example Office')
    custom.locator('[data-field=cidr]').fill('192.168.10.64/27')
    for vlan,cidr in [('DATA','10.31.49.0/24'),('WIRELESS','10.231.49.0/24'),('VOIP','10.131.49.0/24')]:
        custom.locator('#add').click()
        row=custom.locator('#scopes tr').last
        row.locator('select').select_option(vlan)
        row.locator('[data-field=cidr]').fill(cidr)
        assert row.get_by_label('DHCP start offset').input_value()=='100'
        assert row.get_by_label('DHCP end offset').input_value()=='250'
    data_row=custom.locator('#scopes tr').nth(1)
    data_row.get_by_label('DHCP start offset').fill('50')
    data_row.get_by_label('DHCP start offset').press('Tab')
    assert data_row.get_by_label('DHCP start slider').input_value()=='50'
    wireless_row=custom.locator('#scopes tr').nth(2)
    wireless_row.get_by_label('DHCP end slider').fill('200')
    voip_row=custom.locator('#scopes tr').nth(3)
    voip_row.get_by_label('DHCP start offset').fill('75')
    voip_row.get_by_label('DHCP start offset').press('Tab')
    custom.get_by_role('button',name='Calculate & review').click()
    assert custom.evaluate('review.dhcp.map(r=>r.slice(7))')==[
        ['192.168.10.66','192.168.10.94'],['10.31.49.50','10.31.49.250'],
        ['10.231.49.100','10.231.49.200'],['10.131.49.75','10.131.49.250']]
    assert 'Address Pool: 10.31.49.50 - 250' in custom.evaluate('dhcpText(review.dhcp)')
    custom.reload()
    assert custom.locator('#scopes tr').nth(1).get_by_label('DHCP start offset').input_value()=='50'
    assert custom.locator('#scopes tr').nth(2).get_by_label('DHCP end offset').input_value()=='200'
    assert custom.locator('#scopes tr').nth(3).get_by_label('DHCP start offset').input_value()=='75'
    custom.locator('#scopes tr').nth(1).get_by_role('button',name='Reset range').click()
    assert custom.locator('#scopes tr').nth(1).get_by_label('DHCP start offset').input_value()=='100'
    custom.close()
    # Custom switch variable columns: defaults, per-device override, CSV quoting, URL round-trip.
    custom=browser.new_page(viewport={'width':1440,'height':1100},accept_downloads=True)
    custom.on('pageerror',lambda e:errors.append(str(e)))
    custom.goto(shared_url.split('#')[0])
    custom.locator('#site').fill('Example Office')
    custom.locator('#prefix').fill('uk-xx')
    custom.locator('#core').fill('1')
    custom.locator('#access').fill('1')
    custom.locator('[data-field=cidr]').fill('192.168.10.64/27')
    custom.locator('#build').click()
    custom.locator('#addParam').click()
    custom.get_by_label('Custom parameter name').nth(0).fill('_sys_location')
    custom.get_by_label('Custom parameter default').nth(0).fill('Head office')
    custom.locator('#addParam').click()
    custom.get_by_label('Custom parameter name').nth(1).fill('_sys_tag')
    custom.get_by_label('Custom parameter default').nth(1).fill('Core, building "A"')
    drows=custom.locator('#devices tr')
    assert drows.count()==2
    assert drows.nth(0).locator('input').nth(2).input_value()=='Head office'
    drows.nth(1).locator('input').nth(2).fill('Branch office')
    assert drows.nth(1).locator('input').nth(3).input_value()=='Core, building "A"'
    for i in range(2):
        drows.nth(i).locator('input').nth(0).fill(f'CUSTOM{i+1}')
        drows.nth(i).locator('input').nth(1).fill(f'AA:BB:CC:DD:EE:{i+1:02X}')
    custom.locator('#build').click()
    assert custom.locator('#devices tr').nth(1).locator('input').nth(2).input_value()=='Branch office'
    custom.get_by_role('button',name='Calculate & review').click()
    assert custom.locator('#varsDownload').is_enabled()
    assert custom.evaluate('review.varsHeaders')[-2:]==['_sys_location','_sys_tag']
    assert custom.evaluate('review.vars[0]')[-2:]==['Head office','Core, building "A"']
    assert custom.evaluate('review.vars[1]')[-2:]==['Branch office','Core, building "A"']
    with custom.expect_download() as info:
        custom.locator('#varsDownload').click()
    custom_file=ROOT/'tested-custom-variables.csv'
    info.value.save_as(custom_file)
    custom_csv=list(csv.reader(io.StringIO(custom_file.read_text())))
    assert custom_csv[0][-2:]==['_sys_location','_sys_tag']
    assert custom_csv[1][1]=='aa:bb:cc:dd:ee:01'
    assert custom_csv[1][-2:]==['Head office','Core, building "A"']
    assert custom_csv[2][-2:]==['Branch office','Core, building "A"']
    # Individual CSV exports preserve custom field order, defaults and per-device overrides.
    assert custom.locator('.device-file').count()==2
    for name,expected in [
        ('uk-xx-coresw01',['Head office','Core, building "A"']),
        ('uk-xx-accsw01',['Branch office','Core, building "A"']),
    ]:
        with custom.expect_download() as info:
            custom.get_by_role('button',name='Download variables CSV for '+name).click()
        assert info.value.suggested_filename==name+'-variables.csv'
        csv_path=ROOT/('tested-custom-'+name+'.csv')
        info.value.save_as(csv_path)
        dev_rows=list(csv.reader(io.StringIO(csv_path.read_text())))
        assert len(dev_rows)==2
        assert dev_rows[0]==custom_csv[0]
        assert dev_rows[1][4]==name
        assert dev_rows[1][-2:]==expected
        assert dev_rows[1][1].islower()
    assert b'"Core, building ""A"""' in custom_file.read_bytes()
    custom_link=custom.url
    assert '#cfg=2' in custom_link
    restored=browser.new_page()
    restored.on('pageerror',lambda e:errors.append(str(e)))
    restored.goto(custom_link)
    assert restored.get_by_label('Custom parameter name').count()==2
    assert restored.get_by_label('Custom parameter name').nth(0).input_value()=='_sys_location'
    assert restored.get_by_label('Custom parameter default').nth(1).input_value()=='Core, building "A"'
    assert restored.locator('#devices tr').nth(1).locator('input').nth(2).input_value()=='Branch office'
    restored.get_by_role('button',name='Calculate & review').click()
    assert restored.locator('#varsDownload').is_enabled()
    restored.get_by_label('Remove custom parameter').nth(0).click()
    restored.reload()
    assert restored.get_by_label('Custom parameter name').count()==1
    assert restored.get_by_label('Custom parameter name').nth(0).input_value()=='_sys_tag'
    restored.get_by_role('button',name='Calculate & review').click()
    assert restored.evaluate('review.varsHeaders')[-1:] == ['_sys_tag']
    restored.locator('#addParam').click()
    restored.get_by_label('Custom parameter name').nth(1).fill('_SYS_TAG')
    restored.get_by_role('button',name='Calculate & review').click()
    assert 'duplicates an existing CSV column' in restored.locator('#status').inner_text()
    assert restored.locator('#varsDownload').is_disabled()
    assert restored.locator('#dhcpDownload').is_enabled()
    restored.close()
    custom.close()
    # Mobile layout contained in viewport (tables scroll internally).
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not errors, errors
    print(json.dumps({'result':'PASS','subnet_cases':7,'invalid_subnets':5,'exported_switches':7,'exact_example_header':True,'CRLF':True,'download_tests':2,'browser_errors':errors,'checks':['core/access zero padding','shared IP sequence','CIDR preservation','DHCP /24 special range','management DHCP excludes switch IPs','dirty export invalidation','identity preservation','duplicate identity blocking','subnet overlap blocking','DHCP only','mobile width','hosted project URL' if os.environ.get('PLANNER_TEST_URL') else 'offline file URL']},indent=2))
    browser.close()
