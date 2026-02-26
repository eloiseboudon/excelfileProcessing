const BASE = 'https://shop.ajtpro.com';

const PRODUCTS = [

// ===== SMARTPHONES RENFORCÉS =====
{
  id: 'hyper7pro', name: 'Hyper 7 Pro', cat: 'rugged-phones',
  badge: '5G', specs: '16/256 Go · 6,6" FHD+ · 10 800 mAh · 33W · 200MP + 24MP',
  highlights: ['5G', '16 Go', '200MP', '10800 mAh'],
  details: { screen: '6,6" FHD+', ram: '16 Go', storage: '256 Go', battery: '10 800 mAh · 33W', camera: '200MP + 24MP', protection: 'IP68/IP69K · MIL-STD 810G' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/hyper7pro-black.png', url: '/shop/hotwav-hyper-7-pro-5g-ds-16-256gb-black-nfc-19480' },
    { name: 'Red',   hex: '#8b1a1a', img: 'imgs/hyper7pro-red.png',   url: '/shop/hotwav-hyper-7-pro-5g-ds-16-256gb-red-nfc-19481' },
  ],
},
{
  id: 'hyper7', name: 'Hyper 7', cat: 'rugged-phones',
  badge: '5G', specs: '8/256 Go · 6,6" FHD+ · 10 800 mAh · 33W · 64MP',
  highlights: ['5G', '8 Go', '64MP', '10800 mAh'],
  details: { screen: '6,6" FHD+', ram: '8 Go', storage: '256 Go', battery: '10 800 mAh · 33W', camera: '64MP', protection: 'IP68/IP69K · MIL-STD 810G' },
  colors: [
    { name: 'Black',  hex: '#1a1a1a', img: 'imgs/hyper7-black.png',  url: '/shop/hotwav-hyper-7-5g-ds-8-256gb-black-nfc-22487' },
    { name: 'Yellow', hex: '#c8a832', img: 'imgs/hyper7-yellow.png', url: '/shop/hotwav-hyper-7-5g-ds-8-256gb-yellow-nfc-22488' },
  ],
},
{
  id: 'hyper7s', name: 'Hyper 7S', cat: 'rugged-phones',
  badge: '5G', specs: '4/256 Go · 6,6" FHD+ · 10 800 mAh · 33W · 21MP · NFC',
  highlights: ['5G', 'NFC', '10800 mAh'],
  details: { screen: '6,6" FHD+', ram: '4 Go', storage: '256 Go', battery: '10 800 mAh · 33W', camera: '21MP', protection: 'IP68/IP69K · MIL-STD 810H' },
  colors: [
    { name: 'Phoenix Black', hex: '#1a1a1a', img: 'imgs/hyper7s-black.png',  url: '/shop/hotwav-hyper-7s-5g-ds-4-256gb-phoenix-black-24350' },
    { name: 'Punk Yellow',   hex: '#d4c832', img: 'imgs/hyper7s-yellow.png', url: '/shop/hotwav-hyper-7s-5g-ds-4-256gb-punk-yellow-24349' },
  ],
},
{
  id: 'hyper8pro', name: 'Hyper 8 Pro', cat: 'rugged-phones',
  badge: '5G', specs: '12/512 Go · 6,6" FHD+ · 10 800 mAh · 33W · 108MP',
  highlights: ['5G', '12 Go', '512 Go', '108MP'],
  details: { screen: '6,6" FHD+', ram: '12 Go', storage: '512 Go', battery: '10 800 mAh · 33W', camera: '108MP', protection: 'IP68/IP69K · MIL-STD 810H' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/hyper8pro-black.png', url: '/shop/hotwav-hyper-8-pro-5g-ds-12-512gb-black-25329' },
  ],
},
{
  id: 'hyper8ultra', name: 'Hyper 8 Ultra', cat: 'rugged-phones',
  badge: '5G', specs: '12/512 Go · 6,6" FHD+ · 10 800 mAh · 33W · 108MP · Walkie-Talkie',
  highlights: ['5G', 'Walkie-Talkie', '512 Go', '108MP'],
  details: { screen: '6,6" FHD+', ram: '12 Go', storage: '512 Go', battery: '10 800 mAh · 33W', camera: '108MP', protection: 'IP68/IP69K · MIL-STD 810H' },
  colors: [
    { name: 'Bronze Gold', hex: '#b8860b', img: 'imgs/hyper8ultra-gold.png', url: '/shop/hotwav-hyper-8-ultra-5g-ds-12-512gb-gold-25330' },
  ],
},
{
  id: 'cyber16pro', name: 'Cyber 16 Pro', cat: 'rugged-phones',
  badge: '4G', specs: '8/512 Go · 6,6" 2K · 10 800 mAh · 33W · 108MP + 32MP · NFC',
  highlights: ['2K', 'NFC', '512 Go', '108MP'],
  details: { screen: '6,6" 2K', ram: '8 Go', storage: '512 Go', battery: '10 800 mAh · 33W', camera: '108MP + 32MP', protection: 'IP68/IP69K · MIL-STD 810H' },
  colors: [
    { name: 'Gold',  hex: '#c4a35a', img: 'imgs/cyber16pro-gold.png',  url: '/shop/hotwav-cyber-16-pro-4g-ds-8-512gb-gold-nfc-24351' },
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/cyber16pro-black.png', url: '/shop/hotwav-cyber-16-pro-4g-ds-8-512gb-black-nfc-24352' },
  ],
},
{
  id: 'cyber15', name: 'Cyber 15', cat: 'rugged-phones',
  badge: '4G', specs: '12/256 Go · 6,6" FHD+ · 6 280 mAh · 33W · 200MP + 24MP',
  highlights: ['12 Go', '200MP', '33W'],
  details: { screen: '6,6" FHD+', ram: '12 Go', storage: '256 Go', battery: '6 280 mAh · 33W', camera: '200MP + 24MP', protection: 'IP68/IP69K · MIL-STD 810G' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/cyber15-black.png', url: '/shop/hotwav-cyber-15-4g-ds-12-256gb-black-nfc-19592' },
    { name: 'Gold',  hex: '#c4a35a', img: 'imgs/cyber15-gold.png',  url: '/shop/hotwav-cyber-15-4g-ds-12-256gb-gold-nfc-19593' },
  ],
},
{
  id: 'cyber13', name: 'Cyber 13', cat: 'rugged-phones',
  badge: '4G', specs: '8/128 Go · 6,6" HD+ · 10 800 mAh · 64MP',
  highlights: ['8 Go', '10800 mAh', '64MP'],
  details: { screen: '6,6" HD+', ram: '8 Go', storage: '128 Go', battery: '10 800 mAh', camera: '64MP', protection: 'IP68/IP69K · MIL-STD 810H' },
  colors: [
    { name: 'Black',  hex: '#1a1a1a', img: 'imgs/cyber13-black.png',  url: '/shop/hotwav-cyber-13-4g-ds-8-128gb-black-nfc-19483' },
    { name: 'Orange', hex: '#e07020', img: 'imgs/cyber13-orange.png', url: '/shop/hotwav-cyber-13-4g-ds-8-128gb-orange-nfc-19484' },
  ],
},
{
  id: 't7pro', name: 'T7 Pro', cat: 'rugged-phones',
  badge: '4G', specs: '6/256 Go · 6,6" FHD+ · 6 280 mAh · 20W · 64MP · NFC',
  highlights: ['NFC', '64MP', '20W'],
  details: { screen: '6,6" FHD+', ram: '6 Go', storage: '256 Go', battery: '6 280 mAh · 20W', camera: '64MP', protection: 'IP68/IP69K · MIL-STD 810G' },
  colors: [
    { name: 'Black',  hex: '#1a1a1a', img: 'imgs/t7pro-black.png',  url: '/shop/hotwav-t7-pro-4g-ds-6-256gb-black-nfc-19511' },
    { name: 'Orange', hex: '#e07020', img: 'imgs/t7pro-orange.png', url: '/shop/hotwav-t7-pro-4g-ds-6-256gb-orange-nfc-19487' },
  ],
},
{
  id: 't7', name: 'T7', cat: 'rugged-phones',
  badge: '4G', specs: '4/128 Go · 6,52" HD+ · 6 280 mAh · 20MP',
  highlights: ['6280 mAh', 'IP69K'],
  details: { screen: '6,52" HD+', ram: '4 Go', storage: '128 Go', battery: '6 280 mAh', camera: '20MP', protection: 'IP68/IP69K · MIL-STD 810G' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/t7-black.png', url: '/shop/hotwav-t7-4g-ds-4-128gb-black-19485' },
    { name: 'Red',   hex: '#8b1a1a', img: 'imgs/t7-red.png',   url: '/shop/hotwav-t7-4g-ds-4-128gb-red-19486' },
  ],
},
{
  id: 't7s', name: 'T7S', cat: 'rugged-phones',
  badge: '4G', specs: '4/128 Go · 6,52" HD+ · 6 280 mAh · 21MP',
  highlights: ['6280 mAh', 'IP69K'],
  details: { screen: '6,52" HD+', ram: '4 Go', storage: '128 Go', battery: '6 280 mAh', camera: '21MP', protection: 'IP68/IP69K · MIL-STD 810H' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/t7s-black.png',  url: '/shop/hotwav-t7s-4g-ds-4-128gb-black-19594' },
    { name: 'Green', hex: '#2d5a2d', img: 'imgs/t7s-green.png', url: '/shop/hotwav-t7s-4g-ds-4-128gb-green-19595' },
  ],
},

// ===== SMARTPHONES =====
{
  id: 'note18gt', name: 'Note 18 GT', cat: 'phones',
  badge: '4G', specs: '8/256 Go · 7,2" HD+ · 6 200 mAh · 20W · 13MP · NFC',
  highlights: ['7,2"', 'NFC', '8 Go', '256 Go'],
  details: { screen: '7,2" HD+', ram: '8 Go', storage: '256 Go', battery: '6 200 mAh · 20W', camera: '13MP', protection: '—' },
  colors: [
    { name: 'Midnight Black', hex: '#1a1a2e', img: 'imgs/note18gt-black.png', url: '/shop/hotwav-note-18-gt-4g-ds-8-256gb-midnight-black-72-24358' },
    { name: 'Desert Gold',    hex: '#c4a35a', img: 'imgs/note18gt-gold.png',  url: '/shop/hotwav-note-18-gt-4g-ds-8-256gb-desert-gold-72-24357' },
    { name: 'Mint Green',     hex: '#8fbc8f', img: 'imgs/note18gt-green.png', url: '/shop/hotwav-note-18-gt-4g-ds-8-256gb-mint-green-72-24356' },
  ],
},
{
  id: 'note18pro', name: 'Note 18 Pro', cat: 'phones',
  badge: '4G', specs: '6/128 Go · 7,2" HD+ · 6 200 mAh · 20W · 13MP · NFC',
  highlights: ['7,2"', 'NFC', '6 Go'],
  details: { screen: '7,2" HD+', ram: '6 Go', storage: '128 Go', battery: '6 200 mAh · 20W', camera: '13MP', protection: '—' },
  colors: [
    { name: 'Midnight Black', hex: '#1a1a2e', img: 'imgs/note18pro-black.png', url: '/shop/hotwav-note-18-pro-4g-ds-6-128gb-midnight-black-72-24353' },
    { name: 'Desert Gold',    hex: '#c4a35a', img: 'imgs/note18pro-gold.png',  url: '/shop/hotwav-note-18-pro-4g-ds-6-128gb-desert-gold-72-24354' },
    { name: 'Mint Green',     hex: '#8fbc8f', img: 'imgs/note18pro-green.png', url: '/shop/hotwav-note-18-pro-4g-ds-6-128gb-mint-green-72-24355' },
  ],
},
{
  id: 'note16pro', name: 'Note 16 Pro', cat: 'phones',
  badge: '4G', specs: '4/128 Go · 6,9" HD+ · 5 160 mAh · 10W · 13MP',
  highlights: ['6,9"', '128 Go'],
  details: { screen: '6,9" HD+', ram: '4 Go', storage: '128 Go', battery: '5 160 mAh · 10W', camera: '13MP', protection: '—' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/note16pro-black.png', url: '/shop/hotwav-note-16-pro-4g-ds-4-128gb-black-69-22492' },
    { name: 'Gold',  hex: '#c4a35a', img: 'imgs/note16pro-gold.png',  url: '/shop/hotwav-note-16-pro-4g-ds-4-128gb-gold-69-22493' },
    { name: 'Red',   hex: '#8b1a1a', img: 'imgs/note16pro-red.png',   url: '/shop/hotwav-note-16-pro-4g-ds-4-128gb-red-69-22494' },
  ],
},
{
  id: 'note16', name: 'Note 16', cat: 'phones',
  badge: '4G', specs: '4/64 Go · 6,9" HD+ · 5 160 mAh · 10W · 13MP',
  highlights: ['6,9"', '64 Go'],
  details: { screen: '6,9" HD+', ram: '4 Go', storage: '64 Go', battery: '5 160 mAh · 10W', camera: '13MP', protection: '—' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/note16-all.png', url: '/shop/hotwav-note-16-4g-ds-4-64gb-black-69-22489' },
    { name: 'Blue',  hex: '#4169e1', img: 'imgs/note16-all.png', url: '/shop/hotwav-note-16-4g-ds-4-64gb-blue-69-22490' },
    { name: 'Gold',  hex: '#c4a35a', img: 'imgs/note16-all.png', url: '/shop/hotwav-note-16-4g-ds-4-64gb-gold-69-22491' },
  ],
},
{
  id: 'note15pro', name: 'Note 15 Pro', cat: 'phones',
  badge: '4G', specs: '4/128 Go · 6,6" HD+ · 5 160 mAh · 10W · 13MP',
  highlights: ['128 Go', 'IP68'],
  details: { screen: '6,6" HD+', ram: '4 Go', storage: '128 Go', battery: '5 160 mAh · 10W', camera: '13MP', protection: '—' },
  colors: [
    { name: 'Black',         hex: '#1a1a1a', img: 'imgs/note15pro-black.png',       url: '/shop/hotwav-note-15-pro-4g-ds-4-128gb-black-19488' },
    { name: 'Mint Blue',     hex: '#7ec8c8', img: 'imgs/note15pro-mintblue.png',    url: '/shop/hotwav-note-15-pro-4g-ds-4-128gb-mint-blue-19492' },
    { name: 'Phantom Blue',  hex: '#3a3a6e', img: 'imgs/note15pro-phantomblue.png', url: '/shop/hotwav-note-15-pro-4g-ds-4-128gb-phantom-blue-19491' },
  ],
},
{
  id: 'note15', name: 'Note 15', cat: 'phones',
  badge: '4G', specs: '4/64 Go · 6,6" HD+ · 5 160 mAh · 13MP',
  highlights: ['64 Go'],
  details: { screen: '6,6" HD+', ram: '4 Go', storage: '64 Go', battery: '5 160 mAh', camera: '13MP', protection: '—' },
  colors: [
    { name: 'Black',      hex: '#1a1a1a', img: 'imgs/note15-black.png',     url: '/shop/hotwav-note-15-4g-ds-4-64gb-black-19493' },
    { name: 'Indigo',     hex: '#4b0082', img: 'imgs/note15-indigo.png',    url: '/shop/hotwav-note-15-4g-ds-4-64gb-indigo-19495' },
    { name: 'Ocean Blue', hex: '#4682b4', img: 'imgs/note15-oceanblue.png', url: '/shop/hotwav-note-15-4g-ds-4-64gb-ocean-blue-19494' },
  ],
},
{
  id: 'note13max', name: 'Note 13 Max', cat: 'phones',
  badge: '4G', specs: '6/256 Go · 6,8" HD+ · 5 160 mAh · 48MP',
  highlights: ['6 Go', '256 Go', '48MP'],
  details: { screen: '6,8" HD+', ram: '6 Go', storage: '256 Go', battery: '5 160 mAh', camera: '48MP', protection: '—' },
  colors: [
    { name: 'Phantom Black',   hex: '#1a1a2e', img: 'imgs/note13max-black.png',  url: '/shop/hotwav-note-13-max-4g-ds-6-256gb-phantom-black-19499' },
    { name: 'Radiant Purple',  hex: '#6a0dad', img: 'imgs/note13max-purple.png', url: '/shop/hotwav-note-13-max-4g-ds-6-256gb-radiant-purple-19501' },
    { name: 'Titan Gold',      hex: '#c4a35a', img: 'imgs/note13max-gold.png',   url: '/shop/hotwav-note-13-max-4g-ds-6-256gb-titan-gold-19534' },
  ],
},
{
  id: 'note13', name: 'Note 13', cat: 'phones',
  badge: '4G', specs: '4/128 Go · 6,6" HD+ · 5 160 mAh · 50MP',
  highlights: ['50MP', '128 Go'],
  details: { screen: '6,6" HD+', ram: '4 Go', storage: '128 Go', battery: '5 160 mAh', camera: '50MP', protection: '—' },
  colors: [
    { name: 'Blue',      hex: '#4169e1', img: 'imgs/note13-blue.png',   url: '/shop/hotwav-note-13-4g-ds-4-128gb-blue-19498' },
    { name: 'Dark Grey', hex: '#404040', img: 'imgs/note13-grey.png',   url: '/shop/hotwav-note-13-4g-ds-4-128gb-dark-grey-19496' },
    { name: 'Purple',    hex: '#6a0dad', img: 'imgs/note13-purple.png', url: '/shop/hotwav-note-13-4g-ds-4-128gb-purple-19497' },
  ],
},
{
  id: 'a17promax', name: 'A17 Pro Max', cat: 'phones',
  badge: '4G', specs: '3/128 Go',
  highlights: ['128 Go'],
  details: { screen: '—', ram: '3 Go', storage: '128 Go', battery: '—', camera: '—', protection: '—' },
  colors: [
    { name: 'Moonlight Silver', hex: '#c0c0c0', img: 'imgs/a17promax-silver.png', url: '/shop/hotwav-a17-pro-max-4g-ds-3-128gb-moonlight-silver-25163' },
    { name: 'Nebula Black',     hex: '#1a1a2e', img: 'imgs/a17promax-black.png',  url: '/shop/hotwav-a17-pro-max-4g-ds-3-128gb-nebula-black-25162' },
    { name: 'Sunset Orange',    hex: '#e07020', img: 'imgs/a17promax-orange.png', url: '/shop/hotwav-a17-pro-max-4g-ds-3-128gb-sunset-orange-25169' },
  ],
},
{
  id: 'a16promax', name: 'A16 Pro Max', cat: 'phones',
  badge: '4G', specs: '3/64 Go',
  highlights: ['64 Go'],
  details: { screen: '—', ram: '3 Go', storage: '64 Go', battery: '—', camera: '—', protection: '—' },
  colors: [
    { name: 'Pearl White',   hex: '#f0ead6', img: 'imgs/a16promax-white.png', url: '/shop/hotwav-a16-pro-max-4g-ds-3-64gb-pearl-white-25167' },
    { name: 'Space Black',   hex: '#1a1a2e', img: 'imgs/a16promax-black.png', url: '/shop/hotwav-a16-pro-max-4g-ds-3-64gb-space-black-25165' },
    { name: 'Bamboo Green',  hex: '#6b8e5a', img: 'imgs/a16promax-green.png', url: '/shop/hotwav-a16-pro-max-4g-ds-3-64gb-bamboo-green-25166' },
  ],
},
{
  id: 'a56', name: 'A56', cat: 'phones',
  badge: '4G', specs: '3/128 Go',
  highlights: ['128 Go'],
  details: { screen: '—', ram: '3 Go', storage: '128 Go', battery: '—', camera: '—', protection: '—' },
  colors: [
    { name: 'Aurora White',  hex: '#f0ead6', img: 'imgs/a56-white.png', url: '/shop/hotwav-a56-4g-ds-3-128gb-aurora-white-25318' },
    { name: 'Midnight Black', hex: '#1a1a2e', img: 'imgs/a56-black.png', url: '/shop/hotwav-a56-4g-ds-3-128gb-midnight-black-25319' },
    { name: 'Bamboo Green',  hex: '#6b8e5a', img: 'imgs/a56-green.png', url: '/shop/hotwav-a56-4g-ds-3-128gb-bamboo-green-25320' },
  ],
},
{
  id: 'a36', name: 'A36', cat: 'phones',
  badge: '4G', specs: '3/64 Go',
  highlights: ['64 Go'],
  details: { screen: '—', ram: '3 Go', storage: '64 Go', battery: '—', camera: '—', protection: '—' },
  colors: [
    { name: 'Aurora White', hex: '#f0ead6', img: 'imgs/a36-white.png',  url: '/shop/hotwav-a36-4g-ds-3-64gb-aurora-white-25317' },
    { name: 'Satin Black',  hex: '#1a1a1a', img: 'imgs/a36-black.png',  url: '/shop/hotwav-a36-4g-ds-3-64gb-satin-black-25164' },
    { name: 'Neon Orange',  hex: '#ff6600', img: 'imgs/a36-orange.png', url: '/shop/hotwav-a36-4g-ds-3-64gb-neon-orange-25316' },
  ],
},
{
  id: 'a26ultra', name: 'A26 Ultra', cat: 'phones',
  badge: 'soon', specs: '3/128 Go · Bientôt disponible',
  highlights: ['128 Go', 'NOUVEAU'],
  details: { screen: '—', ram: '3 Go', storage: '128 Go', battery: '—', camera: '—', protection: '—' },
  colors: [
    { name: 'Space Black',  hex: '#1a1a2e', img: 'imgs/a26ultra-all.png', url: '#' },
    { name: 'Aurora White', hex: '#f0ead6', img: 'imgs/a26ultra-all.png', url: '#' },
    { name: 'Neon Orange',  hex: '#ff6600', img: 'imgs/a26ultra-all.png', url: '#' },
  ],
},

// ===== TABLETTES RENFORCÉES =====
{
  id: 'tabr9ultra', name: 'TAB R9 Ultra', cat: 'rugged-tabs',
  badge: '5G', specs: '8/512 Go · 11" 2K · 20 080 mAh · 64MP',
  highlights: ['5G', '2K', '20080 mAh', '512 Go'],
  details: { screen: '11" 2K', ram: '8 Go', storage: '512 Go', battery: '20 080 mAh', camera: '64MP', protection: 'IP68/IP69K · MIL-STD 810H' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/tabr9ultra-black.png', url: '/shop/hotwav-tab-r9-ultra-5g-11-8-512gb-black-25328' },
    { name: 'Red',   hex: '#8b1a1a', img: 'imgs/tabr9ultra-red.png',   url: '/shop/hotwav-tab-r9-ultra-5g-11-8-512gb-red-25327' },
  ],
},
{
  id: 'tabr9plus', name: 'TAB R9 Plus', cat: 'rugged-tabs',
  badge: 'LTE', specs: '8/512 Go · 11" 2K · 20 080 mAh · 64MP',
  highlights: ['2K', '20080 mAh', '512 Go'],
  details: { screen: '11" 2K', ram: '8 Go', storage: '512 Go', battery: '20 080 mAh', camera: '64MP', protection: 'IP68/IP69K · MIL-STD 810H' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/tabr9plus-black.png', url: '/shop/hotwav-tab-r9-plus-11-8-512gb-black-lte-24359' },
    { name: 'Red',   hex: '#8b1a1a', img: 'imgs/tabr9plus-red.png',   url: '/shop/hotwav-tab-r9-plus-11-8-512gb-red-lte-24360' },
  ],
},
{
  id: 'tabr9pro', name: 'TAB R9 Pro', cat: 'rugged-tabs',
  badge: 'LTE', specs: '6/256 Go · 11" FHD+ · 20 080 mAh · 20W · 64MP',
  highlights: ['FHD+', '20080 mAh', '20W'],
  details: { screen: '11" FHD+', ram: '6 Go', storage: '256 Go', battery: '20 080 mAh · 20W', camera: '64MP', protection: 'IP68/IP69K · MIL-STD 810G' },
  colors: [
    { name: 'Black', hex: '#1a1a1a', img: 'imgs/tabr9pro-black.png', url: '/shop/hotwav-tab-r9-pro-11-6-256gb-black-lte-19535' },
    { name: 'Red',   hex: '#8b1a1a', img: 'imgs/tabr9pro-red.png',   url: '/shop/hotwav-tab-r9-pro-11-6-256gb-red-lte-19518' },
  ],
},
{
  id: 'tabr10pro', name: 'TAB R10 Pro', cat: 'rugged-tabs',
  badge: 'LTE', specs: '8/256 Go · 10,1" HD+ · 10 800 mAh · 13MP',
  highlights: ['8 Go', '10800 mAh'],
  details: { screen: '10,1" HD+', ram: '8 Go', storage: '256 Go', battery: '10 800 mAh', camera: '13MP', protection: 'IP68/IP69K · MIL-STD 810G' },
  colors: [
    { name: 'Black',  hex: '#1a1a1a', img: 'imgs/tabr10pro-black.png',  url: '/shop/hotwav-tab-r10-pro-10-1-8-256gb-black-lte-22495' },
    { name: 'Orange', hex: '#e07020', img: 'imgs/tabr10pro-orange.png', url: '/shop/hotwav-tab-r10-pro-10-1-8-256gb-orange-lte-22496' },
  ],
},
{
  id: 'tabr8', name: 'TAB R8', cat: 'rugged-tabs',
  badge: 'LTE', specs: '4/128 Go · 10,1" HD+ · 10 800 mAh · 13MP',
  highlights: ['10800 mAh', '128 Go'],
  details: { screen: '10,1" HD+', ram: '4 Go', storage: '128 Go', battery: '10 800 mAh', camera: '13MP', protection: 'IP68/IP69K · MIL-STD 810G' },
  colors: [
    { name: 'Black',  hex: '#1a1a1a', img: 'imgs/tabr8-black.png',  url: '/shop/hotwav-tab-r8-10-1-4-128gb-black-lte-19580' },
    { name: 'Orange', hex: '#e07020', img: 'imgs/tabr8-orange.png', url: '/shop/hotwav-tab-r8-10-1-4-128gb-orange-lte-19596' },
  ],
},
{
  id: 'tabr7', name: 'TAB R7', cat: 'rugged-tabs',
  badge: 'LTE', specs: '6/256 Go · 10,1" HD+ · 15 600 mAh · 16MP',
  highlights: ['15600 mAh', '256 Go'],
  details: { screen: '10,1" HD+', ram: '6 Go', storage: '256 Go', battery: '15 600 mAh', camera: '16MP', protection: 'IP68/IP69K · MIL-STD 810G' },
  colors: [
    { name: 'Grey',   hex: '#808080', img: 'imgs/tabr7-grey.png',   url: '/shop/hotwav-tab-r7-10-1-6-256gb-grey-lte-19507' },
    { name: 'Orange', hex: '#e07020', img: 'imgs/tabr7-orange.png', url: '/shop/hotwav-tab-r7-10-1-6-256gb-orange-lte-19579' },
  ],
},

// ===== TABLETTES =====
{
  id: 'tabpad11', name: 'TAB PAD 11', cat: 'tabs',
  badge: 'LTE', specs: '6/256 Go · 11" 2K · 8 000 mAh · 16MP',
  highlights: ['11"', '2K', '256 Go'],
  details: { screen: '11" 2K', ram: '6 Go', storage: '256 Go', battery: '8 000 mAh', camera: '16MP', protection: '—' },
  colors: [
    { name: 'Grey', hex: '#808080', img: 'imgs/tabpad11-grey.png', url: '/shop/hotwav-tab-pad-11-11-6-256gb-grey-lte-23067' },
  ],
},
{
  id: 'tabpad13pro', name: 'TAB PAD 13 Pro', cat: 'tabs',
  badge: 'LTE', specs: '4/256 Go · 10,1" HD+ · 6 000 mAh · 13MP',
  highlights: ['256 Go', '10,1"'],
  details: { screen: '10,1" HD+', ram: '4 Go', storage: '256 Go', battery: '6 000 mAh', camera: '13MP', protection: '—' },
  colors: [
    { name: 'Twilight Grey', hex: '#6e6e7e', img: 'imgs/tabpad13pro-grey.png',  url: '/shop/hotwav-tab-pad-13-pro-101-4-256gb-twilight-grey-lte-25326' },
    { name: 'Mint Green',    hex: '#8fbc8f', img: 'imgs/tabpad13pro-green.png', url: '/shop/hotwav-tab-pad-13-pro-101-4-256gb-mint-green-lte-25325' },
  ],
},
{
  id: 'tabpad13', name: 'TAB PAD 13', cat: 'tabs',
  badge: 'LTE', specs: '4/128 Go · 10,1" HD+ · 6 000 mAh · 13MP',
  highlights: ['128 Go', '10,1"'],
  details: { screen: '10,1" HD+', ram: '4 Go', storage: '128 Go', battery: '6 000 mAh', camera: '13MP', protection: '—' },
  colors: [
    { name: 'Twilight Grey', hex: '#6e6e7e', img: 'imgs/tabpad13-grey.png',  url: '/shop/hotwav-tab-pad-13-101-4-128gb-twilight-grey-lte-25323' },
    { name: 'Mint Green',    hex: '#8fbc8f', img: 'imgs/tabpad13-green.png', url: '/shop/hotwav-tab-pad-13-101-4-128gb-mint-green-lte-25324' },
  ],
},
{
  id: 'tabpad12', name: 'TAB PAD 12', cat: 'tabs',
  badge: 'LTE', specs: '3/64 Go · 10,1" HD+ · 6 000 mAh · 8MP',
  highlights: ['64 Go', '10,1"'],
  details: { screen: '10,1" HD+', ram: '3 Go', storage: '64 Go', battery: '6 000 mAh', camera: '8MP', protection: '—' },
  colors: [
    { name: 'Twilight Grey', hex: '#6e6e7e', img: 'imgs/tabpad12-all.png', url: '/shop/hotwav-tab-pad-12-101-3-64gb-twilight-grey-lte-25321' },
    { name: 'Misty Blue',    hex: '#7ea8be', img: 'imgs/tabpad12-all.png', url: '/shop/hotwav-tab-pad-12-101-3-64gb-misty-blue-lte-25322' },
  ],
},

];
