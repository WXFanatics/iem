
Ext.namespace('iemdata');

iemdata.nws_products = [
 ['AFD','Area Forecast Discussion'],
 ['HWO','Hazzardous Weather Outlook'],
 ['NOW','Nowcast']
];

iemdata.vtec_phenomena_dict = [
['SV','Severe Thunderstorm'],
['TO','Tornado'],
['MA','Marine'],
['AF','Volcanic Ashfall'],
['AS','Air Stagnation'],
['AV','Avalanche'],
['BS','Blowing Snow'],
['BW','Brisk Wind'],
['BZ','Blizzard'],
['CF','Coastal Flood'],
['DU','Blowing Dust'],
['DS','Dust Storm'],
['EC','Extreme Cold'],
['EH','Excessive Heat'],
['EW','Extreme Wind'],
['FA','Areal Flood'],
['FF','Flash Flood'],
['FL','Flood'],
['FR','Frost'],
['FZ','Freeze'],
['FG','Dense Fog'],
['FW','Red Flag'],
['GL','Gale'],
['HF','Hurricane Force Wind'],
['HI','Inland Hurricane Wind'],
['HS','Heavy Snow'],
['HP','Heavy Sleet'],
['HT','Heat'],
['HU','Hurricane'],
['HW','High Wind'],
['HY','Hydrologic'],
['HZ','Hard Freeze'],
['IS','Ice Storm'],
['IP','Sleet'],
['LB','Lake Effect Snow and Blowing Snow'],
['LE','Lake Effect Snow'],
['LO','Low Water'],
['LS','Lakeshore Flood'],
['LW','Lake Wind'],
['RB','Small Craft for Rough Bar'],
['RH','Radiological Hazard'],
['SB','Snow and Blowing Snow'],
['SC','Small Craft'],
['SE','Hazardous Seas'],
['SI','Small Craft for Winds'],
['SM','Dense Smoke'],
['SN','Snow'],
['SR','Storm'],
['SU','High Surf'],
['TI','Inland Tropical Storm Wind'],
['TR','Tropical Storm'],
['TS','Tsunami'],
['TY','Typhoon'],
['UP','Ice Accretion'],
['VO','Volcano'],
['WC','Wind Chill'],
['WI','Wind'],
['WS','Winter Storm'],
['WW','Winter Weather'],
['ZF','Freezing Fog'],
['ZR','Freezing Rain'],
['ZY','Freezing Spray']
];

iemdata.vtecPhenomenaStore = new Ext.data.SimpleStore({
  fields : ['abbr', 'name'],
  idIndex: 0,
  data   : iemdata.vtec_phenomena_dict
});

iemdata.vtec_sig_dict = [
['W','Warning'],
['Y','Advisory'],
['A','Watch'],
['S','Statement'],
['F','Forecast'],
['O','Outlook'],
['N','Synopsis']
];

iemdata.vtecSignificanceStore = new Ext.data.SimpleStore({
  fields : ['abbr', 'name'],
  idIndex: 0,
  data   : iemdata.vtec_sig_dict
});


iemdata.wfos = [
 ['ABQ','ALBUQUERQUE'],
 ['ABR','ABERDEEN'],
 ['AFC','ANCHORAGE'],
 ['AFG','FAIRBANKS'],
 ['AJK','JUNEAU'],
 ['AKQ','WAKEFIELD'],
 ['ALY','ALBANY'],
 ['AMA','AMARILLO'],
 ['APX','GAYLORD'],
 ['ARX','LA_CROSSE'],
 ['BGM','BINGHAMTON'],
 ['BIS','BISMARCK'],
 ['BMX','BIRMINGHAM'],
 ['BOI','BOISE'],
 ['BOU','DENVER'],
 ['BOX','TAUNTON'],
 ['BRO','BROWNSVILLE'],
 ['BTV','BURLINGTON'],
 ['BUF','BUFFALO'],
 ['BYZ','BILLINGS'],
 ['CAE','COLUMBIA'],
 ['CAR','CARIBOU'],
 ['CHS','CHARLESTON'],
 ['CLE','CLEVELAND'],
 ['CRP','CORPUS_CHRISTI'],
 ['CTP','STATE_COLLEGE'],
 ['CYS','CHEYENNE'],
 ['DDC','DODGE_CITY'],
 ['DLH','DULUTH'],
 ['DMX','DES_MOINES'],
 ['DTX','DETROIT'],
 ['DVN','QUAD_CITIES_IA'],
 ['EAX','KANSAS_CITY/PLEASANT_HILL'],
 ['EKA','EUREKA'],
 ['EPZ','EL_PASO_TX/SANTA_TERESA'],
 ['EWX','AUSTIN/SAN_ANTONIO'],
 ['EYW','KEY WEST (EYW, pre 5/18/06)'],
 ['FFC','PEACHTREE_CITY'],
 ['FGF','EASTERN_NORTH_DAKOTA'],
 ['FGZ','FLAGSTAFF'],
 ['FSD','SIOUX_FALLS'],
 ['FWD','DALLAS/FORT_WORTH'],
 ['GGW','GLASGOW'],
 ['GID','HASTINGS'],
 ['GJT','GRAND_JUNCTION'],
 ['GLD','GOODLAND'],
 ['GRB','GREEN_BAY'],
 ['GRR','GRAND_RAPIDS'],
 ['GSP','GREENVILLE/SPARTANBURG'],
 ['GYX','GRAY'],
 ['HFO','HONOLULU'],
 ['HGX','HOUSTON/GALVESTON'],
 ['HNX','SAN_JOAQUIN_VALLEY/HANFORD'],
 ['HUN','HUNTSVILLE'],
 ['ICT','WICHITA'],
 ['ILM','WILMINGTON'],
 ['ILN','WILMINGTON'],
 ['ILX','LINCOLN'],
 ['IND','INDIANAPOLIS'],
 ['IWX','NORTHERN_INDIANA'],
 ['JAN','JACKSON'],
 ['JAX','JACKSONVILLE'],
 ['JKL','JACKSON'],
 ['KEY','KEY WEST (KEY, post 5/18/06)'],
 ['LBF','NORTH_PLATTE'],
 ['LCH','LAKE_CHARLES'],
 ['LIX','NEW_ORLEANS'],
 ['LKN','ELKO'],
 ['LMK','LOUISVILLE'],
 ['LOT','CHICAGO'],
 ['LOX','LOS_ANGELES/OXNARD'],
 ['LSX','ST_LOUIS'],
 ['LUB','LUBBOCK'],
 ['LWX','BALTIMORE_MD/_WASHINGTON_DC'],
 ['LZK','LITTLE_ROCK'],
 ['MAF','MIDLAND/ODESSA'],
 ['MEG','MEMPHIS'],
 ['MFL','MIAMI'],
 ['MFR','MEDFORD'],
 ['MHX','NEWPORT/MOREHEAD_CITY'],
 ['MKX','MILWAUKEE/SULLIVAN'],
 ['MLB','MELBOURNE'],
 ['MOB','MOBILE'],
 ['MPX','TWIN_CITIES/CHANHASSEN'],
 ['MQT','MARQUETTE'],
 ['MRX','MORRISTOWN'],
 ['MSO','MISSOULA'],
 ['MTR','SAN_FRANCISCO'],
 ['OAX','OMAHA/VALLEY'],
 ['OHX','NASHVILLE'],
 ['OKX','NEW_YORK'],
 ['OTX','SPOKANE'],
 ['OUN','NORMAN'],
 ['PAH','PADUCAH'],
 ['PBZ','PITTSBURGH'],
 ['PDT','PENDLETON'],
 ['PHI','MOUNT_HOLLY'],
 ['PIH','POCATELLO/IDAHO_FALLS'],
 ['PQR','PORTLAND'],
 ['PSR','PHOENIX'],
 ['PUB','PUEBLO'],
 ['RAH','RALEIGH'],
 ['REV','RENO'],
 ['RIW','RIVERTON'],
 ['RLX','CHARLESTON'],
 ['RNK','BLACKSBURG'],
 ['SEW','SEATTLE'],
 ['SGF','SPRINGFIELD'],
 ['SGX','SAN_DIEGO'],
 ['SHV','SHREVEPORT'],
 ['SJT','SAN_ANGELO'],
 ['SJU','SAN_JUAN'],
 ['SLC','SALT_LAKE_CITY'],
 ['STO','SACRAMENTO'],
 ['TAE','TALLAHASSEE'],
 ['TBW','TAMPA_BAY_AREA/RUSKIN'],
 ['TFX','GREAT_FALLS'],
 ['TOP','TOPEKA'],
 ['TSA','TULSA'],
 ['TWC','TUCSON'],
 ['UNR','RAPID_CITY'],
 ['VEF','LAS_VEGAS']
];
