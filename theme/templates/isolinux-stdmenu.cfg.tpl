# BIOS boot menu (isolinux vesamenu) colours. Replaces live-build's
# syslinux_common/stdmenu.cfg; colours are #AARRGGBB.
menu clear
menu background splash.png
menu color title	* #ff{{ colors.text|nohash }} *
menu color border	* #00000000 #00000000 none
menu color unsel	* #ff{{ colors.text|nohash }} #00000000 none
menu color hotkey	* #ff{{ colors.accent|nohash }} #00000000 none
menu color sel		* #ff{{ colors.bg|nohash }} #ff{{ colors.accent|nohash }} none
menu color hotsel	1;7;37;40 #ff{{ colors.bg|nohash }} #ff{{ colors.accent|nohash }} none
menu color tabmsg	* #ff{{ colors.text_dim|nohash }} #00000000 none
menu color help		37;40 #ff{{ colors.text_dim|nohash }} #00000000 none
menu color timeout_msg	* #ff{{ colors.text_dim|nohash }} #00000000 none
menu color timeout	* #ff{{ colors.accent|nohash }} #00000000 none
menu vshift 12
menu rows 10
menu helpmsgrow 15
# The command line must be at least one line from the bottom.
menu cmdlinerow 16
menu timeoutrow 16
menu tabmsgrow 18
menu tabmsg Press ENTER to boot or TAB to edit a menu entry
