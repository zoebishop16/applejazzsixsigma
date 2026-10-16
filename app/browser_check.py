"""Integration checks against a running local app; optional Python Playwright.

python app/browser_check.py --channel msedge
Uses an installed browser channel, or Playwright's Chromium if omitted.
"""
import argparse
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--channel', default=None)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={'width': 1600, 'height': 1080})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        def idle():
            page.wait_for_timeout(500)
            page.wait_for_function("!document.documentElement.classList.contains('shiny-busy') && !document.querySelector('.recalculating')", timeout=60000)
            assert not page.get_by_text('Shiny Client Errors', exact=True).count(), page.locator('body').inner_text()
        response = page.goto(args.url)
        assert response.status == 200
        expect(page.locator('#header h1')).to_have_text('Live Map', timeout=60000)
        expect(page.locator('#body svg.station-map')).to_be_visible(timeout=60000)
        idle()
        page.locator('#body svg .station-node').first.click()
        expect(page.locator('#focus')).not_to_have_value('all')
        idle()
        print('PASS HTTP 200, map markers and station selection')
        page.select_option('#focus', 'all')
        idle()
        page.select_option('#district', 'Residential')
        expect(page.locator('#body .station-node')).to_have_count(5, timeout=30000)
        idle()
        page.select_option('#district', 'all')
        expect(page.locator('#body .station-node')).to_have_count(20, timeout=30000)
        idle()
        print('PASS shared district filters')
        for key, title in [('stockouts','Stockouts & Heatmap'), ('docks','Dock Health'),
                           ('forecast','Forecast & At-Risk'), ('dispatch','Dispatch'),
                           ('maintenance','Maintenance'), ('analysis','Data Analysis')]:
            page.locator(f'input[name="page"][value="{key}"]').check(force=True)
            expect(page.locator('#header h1')).to_have_text(title, timeout=30000)
            expect(page.locator('#body')).not_to_contain_text('Analysis needs more information', timeout=30000)
            idle()
            assert not page.locator('.shiny-output-error').count(), page.locator('body').inner_text()
            print(f'PASS page {title}')
        for tab in ['capability','reliability','fmea','control']:
            page.locator(f'input[name="analysis_tab"][value="{tab}"]').check(force=True)
            idle()
            assert not page.locator('.shiny-output-error').count()
            assert 'Analysis needs more information' not in page.locator('#body').inner_text()
            print(f'PASS analysis {tab}')
        for chart in ['imr','hourly','p']:
            if chart == 'hourly':
                page.select_option('#focus', 'S01')
                idle()
            elif chart == 'p':
                page.select_option('#focus', 'all')
                idle()
            page.select_option('#chart_type', chart)
            idle()
            assert 'Analysis needs more information' not in page.locator('#body').inner_text(), page.locator('#body').inner_text()
            print(f'PASS control {chart}')
        page.locator('input[name="analysis_tab"][value="fmea"]').check(force=True)
        idle()
        page.locator('#severity').fill('9')
        page.locator('#severity').press('Tab')
        page.locator('#save_fmea').click()
        expect(page.locator('.shiny-notification')).to_contain_text('FMEA scores updated', timeout=30000)
        idle()
        page.locator('input[name="page"][value="dispatch"]').check(force=True)
        idle()
        page.locator('#add_task').click()
        expect(page.locator('#queue_id option')).to_have_count(1)
        expect(page.locator('#queue_id')).to_have_value('Q001', timeout=30000)
        idle()
        page.locator('#assign_task').click()
        expect(page.locator('#body')).to_contain_text('Assigned', timeout=30000)
        idle()
        page.locator('#complete_task').click()
        expect(page.locator('#body')).to_contain_text('Completed', timeout=30000)
        idle()
        with page.expect_download() as download:
            page.locator('#export_queue').click()
        target = Path(tempfile.gettempdir()) / 'bikeshare-queue-check.csv'
        download.value.save_as(target)
        assert 'Completed' in target.read_text()
        print('PASS queue add/assign/complete and CSV export')
        page.locator('input[name="page"][value="map"]').check(force=True)
        idle()
        page.select_option('#scenario', 'normal_week')
        idle()
        expect(page.locator('#body .station-node')).to_have_count(20, timeout=30000)
        page.select_option('#scenario', 'improvement_week')
        idle()
        expect(page.locator('#body .station-node')).to_have_count(20, timeout=30000)
        print('PASS scenario switching')
        screenshot = Path(tempfile.gettempdir()) / 'bikeshare-dashboard.png'
        page.screenshot(path=str(screenshot), full_page=True)
        print(f'SCREENSHOT {screenshot}')
        page.set_viewport_size({'width': 390, 'height': 844})
        page.wait_for_timeout(500)
        assert page.locator('#header h1').is_visible()
        print('PASS mobile page visibility')
        page.set_viewport_size({'width': 1600, 'height': 1080})
        page.select_option('#scenario', 'upload')
        expect(page.locator('#body')).to_contain_text('Upload a snapshot CSV', timeout=30000)
        invalid = Path(tempfile.gettempdir()) / 'bikeshare-invalid.csv'
        invalid.write_text('wrong,columns\n1,2\n')
        page.locator('#telemetry').set_input_files(str(invalid))
        expect(page.locator('#body')).to_contain_text('Data could not be loaded', timeout=30000)
        idle()
        valid = Path(tempfile.gettempdir()) / 'bikeshare-known-answer.csv'
        import csv
        with valid.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['timestamp','station_id','station_name','district','latitude','longitude','total_docks','broken_docks','bikes','broken_bikes','service_status','last_reported'])
            for minute, bikes in [(0,5),(5,0),(10,0),(15,5)]:
                stamp = f'2026-09-07T00:{minute:02d}:00Z'
                writer.writerow([stamp,'S01','Known answer','Residential',42,-76,10,0,bikes,0,'operational',stamp])
        page.locator('#telemetry').set_input_files(str(valid))
        expect(page.locator('#metrics')).to_contain_text('50.0%', timeout=30000)
        idle()
        print('PASS known-answer upload: 50.0% observed availability')
        assert not errors, errors
        print('PASS invalid upload error state; no browser JavaScript errors')
        browser.close()


if __name__ == '__main__': main()
