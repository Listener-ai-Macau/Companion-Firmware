"""Customer-facing menu schema; existing backend item IDs remain unchanged.

Locale order matches the production C menu: English, simplified, traditional.
The schema feeds the C row contract and external monochrome label atlas.
"""
TEXT = {
 'MENU':('Menu','菜单','選單'), 'RECORD':('Recording','录音','錄音'),
 'PET':('Pet','宠物','寵物'), 'CONNECT':('Connection','连接','連線'),
 'DEVICE':('Device','设备','裝置'), 'DISPLAY':('Display','显示','顯示'),
 'TIME':('Time & quiet','时间与安静','時間與安靜'), 'GESTURE':('Record gesture','录音手势','錄音手勢'),
 'LANGUAGE':('Language','语言','語言'), 'ABOUT':('About','关于','關於'),
 'STORAGE':('Recordings','录音存储','錄音儲存'), 'SLEEP':('Sleep & battery','休眠与电量','休眠與電量'),
 'CLEAR':('Clear recordings','清空录音','清空錄音'), 'RESTORE':('Restore defaults','恢复默认','恢復預設'),
 'HELP':('Play together','互动玩法','互動玩法'), 'QUICK':('Volume & mute','音量与静音','音量與靜音'),
 'START':('Start recording','开始录音','開始錄音'), 'STOP':('Stop recording','停止录音','停止錄音'),
 'REC_STATE':('Recording state','录音状态','錄音狀態'), 'REC_MODE':('Record mode','录音模式','錄音模式'),
 'REC_LIMIT':('Time limit','录音时限','錄音時限'), 'SILENCE':('Stop on silence','静音自动停止','靜音自動停止'),
 'FOLLOW':('Follow touch','眼神跟随','眼神跟隨'), 'BLINK':('Natural blink','自然眨眼','自然眨眼'),
 'ACTIVITY':('Activity','互动程度','互動程度'), 'CLOCK':('Clock format','时间格式','時間格式'),
 'BAT_STYLE':('Battery style','电量样式','電量樣式'), 'TIMEZONE':('Time zone','时区','時區'),
 'QUIET_HOURS':('Quiet hours','安静时段','安靜時段'), 'PAIR':('Pair a device','配对设备','配對裝置'),
 'LINK_STATE':('Connection','连接状态','連線狀態'), 'LINK_ON':('Connect','开始连接','開始連線'),
 'LINK_OFF':('Disconnect','断开连接','中斷連線'), 'RECONNECT':('Auto reconnect','自动重连','自動重連'),
 'RESET_NAME':('Reset name','重置名称','重設名稱'), 'COUNT':('Recordings','录音数量','錄音數量'),
 'USED':('Space used','已用空间','已用空間'), 'BATTERY':('Battery','电量','電量'),
 'CHARGING':('Charging','充电状态','充電狀態'), 'SLEEP_AFTER':('Sleep after','多久睡着','多久睡著'),
 'SLEEP_NOW':('Sleep now','现在睡觉','現在睡覺'), 'PRODUCT':('Product','产品','產品'),
 'FIRMWARE':('Firmware','固件版本','韌體版本'), 'UI':('UI version','界面版本','介面版本'),
 'PANEL':('Panel','屏幕','螢幕'), 'RESOLUTION':('Resolution','分辨率','解析度'),
 'AUDIO':('Audio format','录音格式','錄音格式'), 'MIC':('Microphone','麦克风','麥克風'),
 'MEDIUM':('Storage medium','存储介质','儲存媒介'), 'REC_SPACE':('Record capacity','录音空间','錄音空間'),
 'UI_SPACE':('UI capacity','资源空间','資源空間'), 'UPDATE':('Updates','升级方式','升級方式'),
 'ID':('Device ID','设备标识','裝置識別碼'),
 'VOICE':('Voice','语音','語音'), 'MEETING':('Meeting','会议','會議'),
 'MIN1':('1 minute','1分钟','1分鐘'), 'MIN3':('3 minutes','3分钟','3分鐘'),
 'MIN5':('5 minutes','5分钟','5分鐘'), 'MIN15':('15 minutes','15分钟','15分鐘'),
 'MIN30':('30 minutes','30分钟','30分鐘'), 'MIN60':('60 minutes','60分钟','60分鐘'),
 'UNLIMITED':('No limit','不限时','不限時'), 'NEVER':('Never','不自动睡','不自動睡'),
 'H24':('24-hour','24小时制','24小時制'), 'H12':('12-hour','12小时制','12小時制'),
 'DIGITS':('Number','数字','數字'), 'FILL':('Fill icon','填充图标','填充圖示'),
 'UTC8':('UTC+08','UTC+08','UTC+08'), 'UTC0':('UTC+00','UTC+00','UTC+00'),
 'UTC5':('UTC-05','UTC-05','UTC-05'), 'Q23':('23:00-07:00','23:00-07:00','23:00-07:00'),
 'Q22':('22:00-08:00','22:00-08:00','22:00-08:00'), 'OFF':('Off','关闭','關閉'),
 'MANUAL':('Manual','手动','手動'),
 'QUIET':('Quiet · Silent replies','安静 · 无声轻回应','安靜 · 無聲輕回應'),
 'STANDARD':('Standard · Balanced','标准 · 自然陪伴','標準 · 自然陪伴'),
 'LIVELY':('Lively · More playful','活泼 · 爱玩一点','活潑 · 愛玩一點'),
 'CORNER':('Double tap corner','左下角双击','左下角點兩下'), 'PULL':('Pull corner right','左下角右拉','左下角右拉'),
 'ZH':('简体中文','简体中文','简体中文'), 'EN':('English','English','English'), 'TW':('繁體中文','繁體中文','繁體中文'),
 'CONNECTED':('Connected','已连接','已連線'), 'DISCONNECTED':('Disconnected','未连接','未連線'),
 'EINK':('E-ink','电子墨水屏','電子墨水螢幕'), 'BUILTIN':('Built-in','内置','內建'),
 'ONDEVICE':('On-device','机身存储','機身儲存'), 'VIA_TYPE':('Via Type','通过Type','透過Type'),
 'VIEW_TYPE':('View in Type','在Type中查看','在Type中查看'), 'ALL_RECORDINGS':('All recordings','全部录音','全部錄音'),
 'IRREVERSIBLE':('Cannot be undone','此操作不可撤销','此操作無法復原'),
 'KEPT':('Recordings are kept','录音文件会保留','錄音檔案會保留'),
 'CANCEL':('Cancel','取消','取消'), 'CONFIRM_CLEAR':('Clear all','确认清空','確認清空'),
 'CONFIRM_RESTORE':('Restore','确认恢复','確認恢復'),
 'PRODUCT_VALUE':('Companion','Companion','Companion'),
 'RES_VALUE':('200 x 200','200 × 200','200 × 200'),
 'AUDIO_VALUE':('16 kHz','16 kHz','16 kHz'),
 'CHARGE_NOW':('Charging','正在充电','正在充電'),
 'POWERED':('External power','外接供电','外接供電'),
 'CHARGE_FAULT':('Charge fault','充电异常','充電異常'),
 'SAY_HI':('Say hi','打招呼','打招呼'),
 'LOOK_WITH_ME':('Gaze game','眼神小游戏','眼神小遊戲'),
 'FILES':('Find on computer','电脑找录音','電腦找錄音'),
 'FILES_ON_PC':('Type: Windows app','Type是Windows软件','Type是Windows軟體'),
 'OPEN_TYPE':('1 Open Type','1 电脑打开Type','1 電腦開啟Type'),
 'CONNECT_FILE':('2 Bluetooth in Type','2 Type连蓝牙','2 Type連藍牙'),
 'LISTEN_FILE':('3 Recordings','3 进入录音列表','3 開啟錄音清單'),
 'SAVED_PC':('Saved · PC Type','已保存 · 电脑Type','已儲存 · 電腦Type'),
 'HOLD_MENU':('Hold menu; 2x ↙ record','长按菜单 · 左下双击录音','長按選單 · 左下雙擊錄音'),
 'INTRO_PULL':('Hold menu; swipe ↙→ rec','长按菜单 · 左下右滑录音','長按選單 · 左下右滑錄音')
}
# view, kind, target (absolute view), backend item, label key.
ROWS = [
 (15,2,255,0,'OPEN_TYPE'),(15,2,255,0,'CONNECT_FILE'),(15,2,255,0,'LISTEN_FILE'),
 (16,1,17,1,'RECORD'),(16,1,24,3,'PET'),(16,1,19,4,'CONNECT'),(16,1,31,0,'DEVICE'),
 (17,3,255,10,'START'),(17,2,255,9,'REC_STATE'),(17,1,15,63,'FILES'),(17,6,255,11,'REC_MODE'),
 (17,1,21,41,'GESTURE'),(17,6,255,12,'REC_LIMIT'),(17,5,255,13,'SILENCE'),
 (18,6,255,16,'CLOCK'),(18,6,255,19,'BAT_STYLE'),
 (19,2,255,20,'LINK_STATE'),(19,3,255,21,'PAIR'),(19,3,255,22,'LINK_ON'),
 (19,5,255,23,'RECONNECT'),(19,3,255,25,'RESET_NAME'),
 (20,6,255,28,'TIMEZONE'),(20,6,255,29,'QUIET_HOURS'),
 (21,4,255,31,'CORNER'),(21,4,255,32,'PULL'),
 (22,4,255,33,'ZH'),(22,4,255,34,'EN'),(22,4,255,62,'TW'),
 (23,2,255,35,'PRODUCT'),(23,2,255,36,'FIRMWARE'),(23,2,255,37,'UI'),
 (23,2,255,17,'PANEL'),(23,2,255,18,'RESOLUTION'),(23,2,255,14,'AUDIO'),
 (23,2,255,15,'MIC'),(23,2,255,49,'MEDIUM'),(23,2,255,50,'REC_SPACE'),
 (23,2,255,51,'UI_SPACE'),(23,2,255,38,'UPDATE'),(23,2,255,39,'ID'),
 (24,3,255,57,'LOOK_WITH_ME'),(24,3,255,56,'SAY_HI'),(24,1,29,0,'HELP'),
 (24,6,255,42,'ACTIVITY'),(24,5,255,43,'FOLLOW'),(24,5,255,44,'BLINK'),
 (25,2,255,46,'COUNT'),(25,2,255,47,'USED'),(25,1,27,48,'CLEAR'),
 (26,2,255,52,'BATTERY'),(26,2,255,53,'CHARGING'),(26,6,255,54,'SLEEP_AFTER'),(26,3,255,55,'SLEEP_NOW'),
 (31,1,30,0,'QUICK'),(31,1,18,0,'DISPLAY'),(31,1,26,0,'SLEEP'),(31,1,20,0,'TIME'),
 (31,1,22,27,'LANGUAGE'),(31,1,25,5,'STORAGE'),(31,1,23,8,'ABOUT'),(31,1,28,30,'RESTORE')
]
TITLES={15:'FILES_ON_PC',16:'MENU',17:'RECORD',18:'DISPLAY',19:'CONNECT',20:'TIME',21:'GESTURE',22:'LANGUAGE',
        23:'ABOUT',24:'PET',25:'STORAGE',26:'SLEEP',27:'CLEAR',28:'RESTORE',29:'HELP',30:'QUICK',31:'DEVICE'}
CHOICES={11:['VOICE','MEETING'],12:['MIN15','MIN30','MIN60','UNLIMITED'],16:['H24','H12'],
         19:['DIGITS','FILL'],28:['UTC8','UTC0','UTC5'],29:['Q23','Q22','OFF'],
         42:['QUIET','STANDARD','LIVELY'],54:['MIN1','MIN3','MIN5','NEVER']}
CHOICE_TITLES={11:'REC_MODE',12:'REC_LIMIT',16:'CLOCK',19:'BAT_STYLE',28:'TIMEZONE',29:'QUIET_HOURS',42:'ACTIVITY',54:'SLEEP_AFTER'}

def write_contract(path):
    keys=list(TEXT);label=lambda k:keys.index(k)
    # Only navigation rows use target; all other authored targets are255.
    # Store kind3/target5 together, expand to the unchanged public5-byte row.
    assert all((r[1]==1 and 0<=r[2]<32) or (r[1]!=1 and r[2]==255) for r in ROWS)
    assert all(0<=r[1]<8 for r in ROWS)
    a=['/* Generated by tools/wba_customer_menu.py. Backend IDs are retained. */',
       '#ifndef COMPANION_CUSTOMER_MENU_CONTRACT_H','#define COMPANION_CUSTOMER_MENU_CONTRACT_H',
       '#include <stdint.h>',
       'typedef struct {uint8_t view,kind,target,item,label;} comp_customer_menu_row_t;',
       '#define COMP_CUSTOMER_CHOICE_BASE 32u','#define COMP_CUSTOMER_DEVICE_VIEW 31u',
       '#define COMP_CUSTOMER_FILE_HELP_VIEW 15u',
       f'#define COMP_CUSTOMER_LABEL_COUNT {len(keys)}u',
       'enum {'+','.join('COMP_CUSTOM_'+k+'='+str(i) for i,k in enumerate(keys))+'};',
       '#ifdef COMP_CUSTOMER_MENU_TABLES',
       'typedef struct {uint8_t view,kind_target,item,label;} comp_customer_menu_packed_row_t;',
       f'static const comp_customer_menu_packed_row_t comp_customer_rows[{len(ROWS)}]={{']
    a += ['{'+','.join(map(str,(r[0],(r[1]<<5)|(r[2] if r[1]==1 else 0),r[3],label(r[4]))))+'},' for r in ROWS]
    a += ['};','#endif','#endif','']
    path.write_text('\n'.join(a),encoding='ascii')
