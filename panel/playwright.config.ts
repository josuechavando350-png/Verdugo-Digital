import { defineConfig } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const testDir=process.env.PANEL_TEST_DIR||join(tmpdir(),'verdugo-panel-e2e');
process.env.PANEL_TEST_DIR=testDir;
const python=process.env.PANEL_PYTHON||'python';
export default defineConfig({testDir:'./e2e',workers:1,retries:0,timeout:60000,use:{viewport:{width:390,height:844},launchOptions:process.env.PANEL_CHROMIUM?{executablePath:process.env.PANEL_CHROMIUM}:{}},webServer:[
 {command:`${python} -m tests_panel.serve_fixture operator 8766`,cwd:'..',url:'http://127.0.0.1:8766',reuseExistingServer:false,env:{PANEL_TEST_DIR:testDir}},
 {command:`${python} -m tests_panel.serve_fixture viewer 8767`,cwd:'..',url:'http://127.0.0.1:8767',reuseExistingServer:false,env:{PANEL_TEST_DIR:testDir}}
],reporter:[['list'],['json',{outputFile:'test-results/results.json'}]]});
