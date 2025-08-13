#ifndef LINUX_OS
#include <limits.h>
#include <std.h>
#else
#include <stdbool.h>
#define FALSE false
#define TRUE true
#endif

#include "../includes/rxFilterBands.h"

#ifdef NESIE_HW
#include "nesie_dsp_lib.h"
#elif defined(MINI_NESIE_HW)
#include "mini_nesie_dsp_lib.h"
#elif defined(NESIE2_HW)
#include "nesie2_dsp_lib.h"
#elif defined(TACTICAL_NESIE_HW)
#include "tactical_nesie_dsp_lib.h"
#else
#endif




#undef printf
//#define printf(my_args...) LOG_printf(&NDL_trace, my_args)
#define printf(my_args...)


// N.B. For Ladon, this table is also used for txFilterBands.

// Before moving filter definitions below consider the constants in rxFilterBands.h
// NOT_FITTED_FILTER_ID, WIDEBAND_FILTER_ID, BOTTOM_850UL_FILTER_ID &
// FILTER_BLOCK0_START .. FILTER_BLOCK4_START


#ifndef LINUX_OS
#pragma DATA_SECTION(rxFilterBands, "SDRAM_INIT_DATA")
#endif
RxFilterBand_t const rxFilterBands[] = {
//    Uplink (dMHz)      Downlink (dMHz)       Direction        Ladon        Band                LTE Band   extra   872 Radio Board Characteristic Data     HW Band     Common
//     From   To         From   To              Mask             Id                             Id,#,total#  data   Table Lookup Id                         id id   U/D name
//    --------------     --------------     -----------------   -----   -----------------       ----------- -----   -----------------------------------     -- --   --  -------
// Block 0 (Generic):
    {{    0,     0},    {    0,     0},     BOTH_DIR_MASK,       0,     BAND_FILTER_EMPTY,      -1, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x00      -   Not fitted
    {{  100, 63000},    {    0,     0},     UPLINK_DIR_MASK,     1,     BAND_FILTER_WIDE,        0, 1,  1,  0,       COVERT872CALDATALOOKUP_WIDEBAND},  //  0x01      -   Wideband        // Location "WIDEBAND_FILTER_ID" MUST BE the Wideband Option.

    // Block 1 (Classic NESIE Standard Filters):
    {{ 4510,  4590},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_CDMA450,    31, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x02 31   UL  450 GSM    Odd! Rev band is 8 MHz, FWD is 7
    {{    0,     0},    { 4600,  4670},     DOWNLINK_DIR_MASK,   0,     BAND_FILTER_CDMA450,    31, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x03      DL     "
    {{ 8060,  8210},    {    0,     0},     UPLINK_DIR_MASK,    11,     BAND_FILTER_IDEN,       27, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x04 27   UL  800 SMR (iDEN)
    {{    0,     0},    { 8510,  8660},     DOWNLINK_DIR_MASK,  10,     BAND_FILTER_IDEN,       27, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x05      DL     "
    {{ 8240,  8490},    {    0,     0},     UPLINK_DIR_MASK,     5,     BAND_FILTER_GSM850,      5, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x06  5   UL  850 GSM
    {{    0,     0},    { 8690,  8940},     DOWNLINK_DIR_MASK,   4,     BAND_FILTER_GSM850,      5, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x07      DL     "
    {{ 8800,  9150},    {    0,     0},     UPLINK_DIR_MASK,     3,     BAND_FILTER_EGSM900,     8, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x08  8   UL  900 EGSM
    {{    0,     0},    { 9250,  9600},     DOWNLINK_DIR_MASK,   2,     BAND_FILTER_EGSM900,     8, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x09      DL     "
    {{17100, 17850},    {    0,     0},     UPLINK_DIR_MASK,     7,     BAND_FILTER_DCS1800,     3, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x0a  3   UL  1800+ DCS
    {{    0,     0},    {18050, 18800},     DOWNLINK_DIR_MASK,   6,     BAND_FILTER_DCS1800,     3, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x0b      DL     "
    {{18500, 19100},    {    0,     0},     UPLINK_DIR_MASK,     9,     BAND_FILTER_PCS1900,     2, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x0c  2   UL  1900 PCS
    {{    0,     0},    {19300, 19900},     DOWNLINK_DIR_MASK,   8,     BAND_FILTER_PCS1900,     2, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x0d      DL     "
    {{19200, 19800},    {    0,     0},     UPLINK_DIR_MASK,    13,     BAND_FILTER_3GBAND1,     1, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x0e  1   UL  2100
    {{    0,     0},    {21100, 21700},     DOWNLINK_DIR_MASK,  12,     BAND_FILTER_3GBAND1,     1, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x0f      DL   "

//// Block 2 (Classic NESIE Additional LTE Filters):
    {{ 8320,  8620},    {    0,     0},     UPLINK_DIR_MASK,    19,     BAND_FILTER_LTE20,      20, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x10 20   UL  800-DD  Note Uplink is higher freq than downlink for LTE20
    {{    0,     0},    { 7910,  8210},     DOWNLINK_DIR_MASK,  18,     BAND_FILTER_LTE20,      20, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x11      DL    "
    {{25000, 25700},    {    0,     0},     UPLINK_DIR_MASK,    17,     BAND_FILTER_LTE7,        7, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x12  7   UL  2600
    {{    0,     0},    {26200, 26900},     DOWNLINK_DIR_MASK,  16,     BAND_FILTER_LTE7,        7, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x13      DL   "

    {{ 8240,  8319},    {    0,     0},     UPLINK_DIR_MASK,     5,     BAND_FILTER_GSM850,      5, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x14  5   UL  850 GSM When LTE-20 UL is present we use filter instead of 850 UL,
                                                                            //                      but that doesn't cover the whole band to use this hypothetical filter
                                                                            //                      so the 850 UL is used at the bottom of the band
                                                                            //                      must be in location 0x14 / 20 unless BOTTOM_850UL_FILTER_ID constant is changed


//// Block 3 (Covert NESIE Standard Filters Implemented in Duplexors (Fwd/Rev paired)):
    {{25000, 25700},    {26200, 26900},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE7,        7, 1,  1,  0,          COVERT872CALDATALOOKUP_LTE_7},  //  0x15  7   UL/DL   2600
    {{17100, 17850},    {18050, 18800},     BOTH_DIR_MASK,       0,     BAND_FILTER_DCS1800,     3, 1,  1,  0,      COVERT872CALDATALOOKUP_DCS1800},  //  0x16  3   UL/DL   1800+ DCS
    {{18500, 19100},    {19300, 19900},     BOTH_DIR_MASK,       0,     BAND_FILTER_PCS1900,     2, 1,  1,  0,      COVERT872CALDATALOOKUP_PCS1900},  //  0x17  3   UL/DL   1900 PCS
    {{19200, 20100},    {21100, 22000},     BOTH_DIR_MASK,       0,     BAND_FILTER_3GBAND1,     1, 1,  1,  0,      COVERT872CALDATALOOKUP_UMTS_1},  //  0x18  1   UL/DL   2100
    {{ 8240,  8490},    { 8690,  8940},     BOTH_DIR_MASK,       0,     BAND_FILTER_GSM850,      5, 1,  1,  0,      COVERT872CALDATALOOKUP_GSM850},  //  0x19  5   UL/DL   850 GSM
    {{ 8800,  9150},    { 9250,  9600},     BOTH_DIR_MASK,       0,     BAND_FILTER_EGSM900,     8, 1,  1,  0,      COVERT872CALDATALOOKUP_EGSM900},  //  0x1A  8   UL/DL   900 EGSM
    {{ 8320,  8620},    { 7910,  8210},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE20,      20, 1,  1,  0,      COVERT872CALDATALOOKUP_LTE_20},  //  0x1B 20   UL/DL   800-DD      Note Uplink is higher freq than downlink for LTE20

//// Block 4 (Covert NESIE Additional LTE Filters Implemented in Duplexors (Fwd/Rev paired), 1st Tranche):
    {{ 7030,  7330},    { 7580,  7880},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE28,      28, 1,  2,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x1C 28   UL/DL   700 APT Lower 2/3rd } Both Duplexors needed to cover the full band
    {{ 7180,  7480},    { 7730,  8030},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE28,      28, 2,  2,  0,      COVERT872CALDATALOOKUP_LTE_28B},  //  0x1D 28   UL/DL   700 APT Upper 2/3rd }   Each covers 2/3rd in both directions

//// Block 5 (Flight/NESIE2 Standard Filters ):
    {{    0,     0},    { 8690,  8940},     DOWNLINK_DIR_MASK,   0,     BAND_FILTER_GSM850,      5, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x1E  5   DL  850 GSM
    {{ 8240,  8490},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_GSM850,      5, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x1F      UL     "
    {{    0,     0},    { 9250,  9600},     DOWNLINK_DIR_MASK,   0,     BAND_FILTER_EGSM900,     8, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x20  8   DL  900 EGSM
    {{ 8800,  9150},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_EGSM900,     8, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x21      UL     "
    {{    0,     0},    {18050, 18800},     DOWNLINK_DIR_MASK,   0,     BAND_FILTER_DCS1800,     3, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x22  3   DL  1800+ DCS
    {{17100, 17850},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_DCS1800,     3, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x23      UL     "
    {{    0,     0},    {19300, 19900},     DOWNLINK_DIR_MASK,   0,     BAND_FILTER_PCS1900,     2, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x24  2   DL  1900 PCS
    {{18500, 19100},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_PCS1900,     2, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x25      UL     "
    {{    0,     0},    {21100, 22000},     DOWNLINK_DIR_MASK,   0,     BAND_FILTER_3GBAND1,     1, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x26  1   DL  2100
    {{19200, 20100},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_3GBAND1,     1, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x27      UL   "
    {{    0,     0},    {26200, 26900},     DOWNLINK_DIR_MASK,   0,     BAND_FILTER_LTE7,        7, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x28  7   DL  2600
    {{25000, 25700},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_LTE7,        7, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x29      UL   "
    {{    0,     0},    { 7910,  8210},     DOWNLINK_DIR_MASK,   0,     BAND_FILTER_LTE20,      20, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x2A 20   DL  800-DD  Note Uplink is higher freq than downlink for LTE20
    {{ 8320,  8620},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_LTE20,      20, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x2B      UL   "

//// Block 6 (Covert NESIE Additional LTE Filters Implemented in Duplexors (Fwd/Rev paired), 2nd Tranche):
    {{ 6980,  7160},    { 7280,  7460},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE12,      12, 1,  1,  0,      COVERT872CALDATALOOKUP_LTE_12},  //  0x2C 12   UL/DL   Lower SMH (Blocks A-C)
    {{ 7770,  7870},    { 7460,  7560},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE13,      13, 1,  1,  0,      COVERT872CALDATALOOKUP_LTE_13},  //  0x2D 13   UL/DL   Upper SMH (Block C)
    {{ 7040,  7160},    { 7340,  7460},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE17,      17, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x2E 14   UL/DL   Lower SMH (Blocks B-C)

//// Block 7 (Tactical NESIE Standard Filters Implemented in Duplexors (Fwd/Rev paired)):
    //DUP300 Qualcom B8659 - LTE7; RF1 Connection on IC300 to pin3 on B8659 Uplink/Reverse ("Tx" with Centre Freq of 2535 MHz), F/R Control line needs to be low for Forward
    {{25000, 25700},    {26200, 26900},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE7,        7, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x2F  7   UL/DL   2600

    //DUP301 Qualcom B8642 - LTE20; RF1 Connection on IC302 to pin3 on B8642 Downlink/Forward ("Rx" with Centre Freq of 806 MHz), F/R Control line needs to be high for Forward
    {{ 8320,  8620},    { 7910,  8210},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE20,      20, 1,  1,  EXTRA_DATA_FORREV_MASK,     COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x30 20   UL/DL   800-DD      Note Uplink is higher freq than downlink for LTE20

    //DUP302 Qualcom B8626 - GSM850/LTE5; RF1 Connection on IC303 to pin3 on B8626 Uplink/Reverse ("Tx" with Centre Freq of 836.5 MHz), F/R Control line needs to be low for Forward
    {{ 8240,  8490},    { 8690,  8940},     BOTH_DIR_MASK,       0,     BAND_FILTER_GSM850,      5, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x31  5   UL/DL   850 GSM

    //FIL300 EPCOS B8515 - GSM900/LTE8; RF1 Connection on IC306 to pin3 on B8515 Uplink/Reverse ("Tx" with Centre Freq of 897.5 MHz), F/R Control line needs to be low for Forward
    {{ 8800,  9150},    { 9250,  9600},     BOTH_DIR_MASK,       0,     BAND_FILTER_EGSM900,     8, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x32  8   UL/DL   900 EGSM

    //FIL301 EPCOS B8088 - DCS1800/LTE3; RF1 Connection on IC307 to pin3 on B8088 Uplink/Reverse ("Tx" with Centre Freq of 1747.5 MHz), F/R Control line needs to be low for Forward
    {{17100, 17850},    {18050, 18800},     BOTH_DIR_MASK,       0,     BAND_FILTER_DCS1800,     3, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x33  3   UL/DL   1800+ DCS

    //FIL302 EPCOS B8078 - DCS1800/LTE2; RF1 Connection on IC309 to pin3 on B8078 Uplink/Reverse ("Tx" with Centre Freq of 1880 MHz), F/R Control line needs to be low for Forward
    {{18500, 19100},    {19300, 19900},     BOTH_DIR_MASK,       0,     BAND_FILTER_PCS1900,     2, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x34  2   UL/DL   1900 PCS

    //DUP303 EPCOS B8550 - UMTS1/LTE1; RF1 Connection on IC314 to pin3 on B8550 Uplink/Reverse ("Tx" with Centre Freq of 1950 MHz), F/R Control line needs to be low for Forward
    {{19200, 20100},    {21100, 22000},     BOTH_DIR_MASK,       0,     BAND_FILTER_3GBAND1,     1, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x35  1   UL/DL   2100

//// Block 8 (Covert NESIE Additional LTE Filters Implemented in Duplexors (Fwd/Rev paired), 3rd Tranche, Forwards and Reverse swapped compared to conventional orientation):
    {{ 7770,  7870},    { 7460,  7560},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE13,      13, 1,  1,  EXTRA_DATA_SWAP_FOR_AND_REV_MASK, COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x36 13   UL/DL   Upper SMH (Block C)

//// Block 9 (Tactical NESIE Additional LTE Filters, 2nd Tranche
    // TDD LTE Band 40 Filter, Uplink arm only connected (Qorvo 885069 BAW Filter)
    {{23000, 24000},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_LTE40,      40, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x37 40   UL/DL (TDD so same band for Both), but tell code it is uplink only so correct branch is chosen


//// Block 10 (Covert NESIE Additional LTE Filter, 4th Tranche
    // TDD LTE Band 40 Filter, Uplink arm only connected (Qorvo 885069 BAW Filter)
    // Currently this is identical to entry 0x37 above, but sensible for Covert to have it's own entry
    {{23000, 24000},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_LTE40,      40, 1,  1,  0,      COVERT872CALDATALOOKUP_LTE_40},  //  0x38 40   UL/DL (TDD so same band for Both), but tell code it is uplink only so correct branch is chosen

    // 856 sub-assembly for LTE28A (lower 2/3rds of the band) uses B8540 filter which has Forward and Reverse paths swapped over relative to most of the other sub-assemblies we use
    // use 0x1C for the "normal" configuration
    {{ 7030,  7330},    { 7580,  7880},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE28,      28, 1,  2,  EXTRA_DATA_SWAP_FOR_AND_REV_MASK,       COVERT872CALDATALOOKUP_LTE_28A},    //  39 28A      UL/DL   700 APT Lower 2/3rd "A"}

//// Block 11 3rd Tranche (Tactical NESIE Additional Filters Implemented in Duplexors (Fwd/Rev paired)), and Single Filters For TDD Bands:
    //FDD LTE Band 25; (Tai-SAW  Technology TF0136A SAW Duplexer) Extended PCS1900 Band
    {{18500, 19200},    {19300, 19950},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE25,      25, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x3A  25  UL/DL

    //FDD LTE Band 26; (Tai-SAW  Technology TF0137A SAW Duplexer) Extended GSM850 Band
    {{8140, 8490},      {8590, 8940},       BOTH_DIR_MASK,       0,     BAND_FILTER_LTE26,      26, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x3B  26  UL/DL

    // TDD LTE Band 38 Filter, Uplink arm only connected (Qorvo 885026 SAW Filter)
    {{25700, 26200},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_LTE38,      38, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x3C 38   UL/DL (TDD so same band for Both), but tell code it is uplink only so correct branch is chosen

    // TDD LTE Band 41 Filter, Uplink arm only connected (Tai-SAW  Technology TA2326C SAW Filter)
    {{24960, 26900},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_LTE41,      41, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x3D 41   UL/DL (TDD so same band for Both), but tell code it is uplink only so correct branch is chosen

    //FDD LTE Band 71; (Murata SAYRL634MBC0B0AR00 SAW Duplexer)
    {{ 6630,  6980},    { 6170,  6520},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE71,      71, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x3E  71  UL/DL

    // TDD NR Band 77 Filter, Uplink arm only connected
    {{33000, 42000},    {    0,     0},     UPLINK_DIR_MASK,     0,     BAND_FILTER_N77,        77, 1,  1,  0,      COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x3F 77   UL/DL (TDD so same band for Both), but tell code it is uplink only so correct branch is chosen

//// Block 12 (Covert NESIE New filter configuration as orignal SAW filter has become obsolete), 5th Covert Tranche
////     This is to be fitted directly to the RF board in manufacture to replace entry 0x1B     
    // DUP5 Taisaw TF0168B Duplexor - LTE20  Forward and Reverse paths swapped over relative to most of the other filters/duplexors we use 
    {{ 8320,  8620},    { 7910,  8210},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE20,      20, 1,  1,  EXTRA_DATA_SWAP_FOR_AND_REV_MASK,      COVERT872CALDATALOOKUP_LTE_20},  //  0x40 20   UL/DL   800-DD      Note Uplink is higher freq than downlink for LTE20
    
//// Block 13 (Tactical NESIE New filter configuration as orignal SAW filter has become obsolete), 4th Tactical Tranche
////     This is to be fitted directly to the RF board in manufacture to replace entry 0x30     
    // DUP101/301 Taisaw TF0168B Duplexor - LTE20, F/R "Control line" needs to be low for Forward 
    {{ 8320,  8620},    { 7910,  8210},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE20,      20, 1,  1,  0,     COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x41 20   UL/DL   800-DD      Note Uplink is higher freq than downlink for LTE20

    // Should we have entries here for LTE12 via 886 board and LTE13 via 887 board? They are already available for Covert via entries 0x2C & 0x2D, but it may prove useful
    // to have distinct entries

//// Block 14 (Tactical NESIE New filter configuration for LTE28 band in one go, rather than needing A & B duplexors, 5th Tactical Tranche
    // muRata SAYRH725MBCOBOA Fullband Band 28 Duplexor - LTE28, F/R "Control line" needs to be low for Forward 
    {{ 7040,  7480},    { 7580,  8030},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE28,      28, 1,  1,  0,     COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x42 28   UL/DL   800-DD


//// Block 15 (Covert NESIE New filter configuration for LTE28 band in one go, rather than needing A & B duplexors, 6th Covert Tranche
    // muRata SAYRH725MBCOBOA Fullband Band 28 Duplexor - LTE28, F/R "Control line" needs to be low for Forward 
    {{ 7040,  7480},    { 7580,  8030},     BOTH_DIR_MASK,       0,     BAND_FILTER_LTE28,      28, 1,  1,  0,     COVERT872CALDATALOOKUP_NO_LOOKUP},  //  0x43 28   UL/DL   800-DD


//// If we add extra filter entries for Flight/NESIE2 we will also need to add extra clauses to the rf_parameters structure in nesie_hw.c

};

unsigned const rxFilterBandsLen = sizeof(rxFilterBands) / sizeof(rxFilterBands[0]);
int8_t const max_lte_band	= MAX_LTE_BAND;	// If we add more filter types we may need to update this



band_filter_t _3gppToNesieBandFilterNumber(unsigned _3gppBandNumber)
{
  switch (_3gppBandNumber) {
    case  1: return BAND_FILTER_3GBAND1;
    case  2: return BAND_FILTER_PCS1900;
    case  3: return BAND_FILTER_DCS1800;
    case  5: return BAND_FILTER_GSM850;
    case  7: return BAND_FILTER_LTE7;
    case  8: return BAND_FILTER_EGSM900;
    case  9: return BAND_FILTER_DCS1800;
    case 12: return BAND_FILTER_LTE12;
    case 13: return BAND_FILTER_LTE13;
    case 17: return BAND_FILTER_LTE17;
    case 20: return BAND_FILTER_LTE20;
    case 25: return BAND_FILTER_LTE25;
    case 26: return BAND_FILTER_LTE26;
    case 27: return BAND_FILTER_IDEN;
    case 28: return BAND_FILTER_LTE28;
    case 31: return BAND_FILTER_CDMA450;
    case 38: return BAND_FILTER_LTE38;
	case 39: return BAND_FILTER_LTE25;
    case 40: return BAND_FILTER_LTE40;
    case 41: return BAND_FILTER_LTE41;
    case 42: return BAND_FILTER_N77;
    case 43: return BAND_FILTER_N77;
    case 52: return BAND_FILTER_N77;
    case 71: return BAND_FILTER_LTE71;
    case 77: return BAND_FILTER_N77;
    case 78: return BAND_FILTER_N77;
    default: return BAND_FILTER_WIDE;
  }
}



//#define	MIN_WIDTH_SEARCH
#define	PASSBAND_CENTRE_SEARCH

duplexor_direction_t test_and_swap_direction(uint8_t extra_data, duplexor_direction_t duplexor_direction_in)
{
	duplexor_direction_t return_value = duplexor_direction_in;

	if ((extra_data & EXTRA_DATA_SWAP_FOR_AND_REV_MASK) == EXTRA_DATA_SWAP_FOR_AND_REV_MASK) {
		if (duplexor_direction_in == DD_UPLINK) {
			return_value = DD_DOWNLINK;
		} else {
			return_value = DD_UPLINK;
		}

	}
	return return_value;
}


int select_rx_filter_site_from_channel_centre_freq(	uint8_t 				 fittedRxFilterIds[],
													int 					 no_of_filter_sites,
													uint32_t				 rx_freq_in_khz,
													uint32_t				 rx_bandwidth_in_khz,
													duplexor_direction_t	*duplexor_direction_ptr,
													uint8_t					*extra_data_ptr
		)
{
	int 		return_value	= NO_FILTER_SITE_AVAILABLE;
    uint16_t	freq_dMHz 		= (uint16_t)((rx_freq_in_khz + 50) / 100);
    uint16_t	low_freq_dMHz	= (uint16_t)((rx_freq_in_khz - (rx_bandwidth_in_khz + 1)/2 + 50) / 100);
    uint16_t	high_freq_dMHz 	= (uint16_t)((rx_freq_in_khz + (rx_bandwidth_in_khz + 1)/2 + 50) / 100);

    if (rx_freq_in_khz >= 6000000) {
    	return return_value;
    }

#ifdef MIN_WIDTH_SEARCH
	{
		int 					site_selector;
		duplexor_direction_t	direction_selector;
		unsigned				min_width 		= UINT_MAX;
		int 					best_selection	= NO_FILTER_SITE_AVAILABLE;

		for (site_selector = 0; site_selector < no_of_filter_sites; site_selector++) {
	        unsigned filterId = fittedRxFilterIds[site_selector];

	        if (filterId < rxFilterBandsLen) {
	        	// Check that we have a sensible ID for the filter site being considered
	        	RxFilterBand const * f = &rxFilterBands[filterId];
		        for (direction_selector = DD_UPLINK; direction_selector < DD_MAX_NO; direction_selector++) {
		        	uint16_t *duplexor_filters_branch_ptr = (uint16_t *)f->uplink_branch;

		        	if ((duplexor_filters_branch_ptr[LOW_FREQ] <= freq_dMHz) && (freq_dMHz <= duplexor_filters_branch_ptr[HIGH_FREQ])) {
		            	// channel centre lies within the passband of the filter
		                unsigned width = duplexor_filters_branch_ptr[HIGH_FREQ] - duplexor_filters_branch_ptr[LOW_FREQ];
		                if (width < min_width) {
		                	// Use the filter with the smallest bandwidth where the wanted frequency is in the pass band
		                	min_width = width;
		                	best_selection = site_selector;
		                	*duplexor_direction_ptr = direction_selector;
		                }
		            }
		        	duplexor_filters_branch_ptr = (uint16_t *)f->downlink_branch;
		        }
	        }
		}
		return_value = best_selection;
	}
#elif defined(PASSBAND_CENTRE_SEARCH)
	{
		int 					site_selector;
		duplexor_direction_t	direction_selector;
		unsigned				min_centre_offset	= UINT_MAX;
		int 					best_selection		= NO_FILTER_SITE_AVAILABLE;
		int						wideband_present	= FALSE;
		int						wideband_site		= NO_FILTER_SITE_AVAILABLE;

		printf("%s, no. of filter site %d, freq %u %u", __func__, no_of_filter_sites, rx_freq_in_khz, freq_dMHz);

		for (site_selector = 0; site_selector < no_of_filter_sites; site_selector++) {
	        unsigned filterId = fittedRxFilterIds[site_selector];


	        if (filterId < rxFilterBandsLen) {
	        	// Check that we have a sensible ID for the filter site being considered
	        	RxFilterBand_t const * f = &rxFilterBands[filterId];

		        printf("%s, %d, %u", __func__, site_selector, filterId);

		        if (filterId == WIDEBAND_FILTER_ID) {
	        		wideband_present 	= TRUE;
	        		wideband_site 		= site_selector;
	        	}

	        	printf("%s - %d, %u,  %u,  %u,  %u,  %u", __func__, site_selector, (uint32_t)f->uplink_branch[0], (uint32_t)f->uplink_branch[1], (uint32_t)f->downlink_branch[0], (uint32_t)f->downlink_branch[1], (uint32_t)f->ladonId);

		        for (direction_selector = DD_UPLINK; direction_selector < DD_MAX_NO; direction_selector++) {
		        	uint16_t *duplexor_filters_branch_ptr = (direction_selector == DD_UPLINK) ? (uint16_t *)f->uplink_branch : (uint16_t *)f->downlink_branch;
//		        	TSK_sleep(1000);

	    	        printf("%s, %d, freq %d, low_edge %d high_edge %d", __func__, site_selector, freq_dMHz, duplexor_filters_branch_ptr[LOW_FREQ], duplexor_filters_branch_ptr[HIGH_FREQ]);

	    	        if ((duplexor_filters_branch_ptr[LOW_FREQ] == 0) || (duplexor_filters_branch_ptr[HIGH_FREQ] == 0)) {
	    	        	continue;
	    	        }

	    	        if ((duplexor_filters_branch_ptr[LOW_FREQ] <= low_freq_dMHz) && (high_freq_dMHz <= duplexor_filters_branch_ptr[HIGH_FREQ])) {
		            	// channel centre lies within the passband of the filter
		            	unsigned band_centre = (duplexor_filters_branch_ptr[LOW_FREQ] + duplexor_filters_branch_ptr[HIGH_FREQ])/2;
		                unsigned centre_offset = (freq_dMHz >= band_centre ? freq_dMHz - band_centre : band_centre - freq_dMHz);

		    	        printf("%s, %d, %u %d - Freq in passband, centre %u, offset %u", __func__, site_selector, filterId, direction_selector, band_centre, centre_offset);

		                if ((centre_offset < min_centre_offset) && (filterId != WIDEBAND_FILTER_ID)) {
		                	// Use the filter where the wanted frequency is closest to the centre of the passband
		                	// Ignore the wideband option here, we might be closer to the middle of that than a proper filter but would use the
		                	// later choice in preference
			    	        printf("%s, %d, %u %d - New Min %d", __func__, site_selector, filterId, direction_selector, centre_offset);
		                	min_centre_offset = centre_offset;
		                	best_selection = site_selector;
		                	*duplexor_direction_ptr = direction_selector;
		                	*extra_data_ptr = f->extra_data;
		                }
		            }
		        }
	        }
		}
		if ((best_selection == NO_FILTER_SITE_AVAILABLE) && (wideband_present == TRUE)) {
			best_selection = wideband_site;
			*duplexor_direction_ptr = DD_UPLINK;
        	*extra_data_ptr = 0;
		}
		return_value = best_selection;
	}
#endif
	printf("%s, normal return value %d", __func__, return_value);
	return	return_value;
}

//#undef printf
//#define printf(my_args...) LOG_printf(&NDL_trace, my_args)

int select_rx_filter_site_from_band_and_channel_centre_freq(	uint8_t 				 fittedRxFilterIds[],
																int 					 no_of_filter_sites,
																uint32_t				 rx_freq_in_khz,
																uint32_t				 rx_bandwidth_in_khz,
																band_filter_t			 filter_band,
																duplexor_direction_t	*duplexor_direction_ptr,
																uint8_t					*extra_data_ptr
	)
{
	int 					return_value	= NO_FILTER_SITE_AVAILABLE;
    uint16_t				freq_dMHz 		= (uint16_t)((rx_freq_in_khz + 50) / 100);
    uint16_t				low_freq_dMHz	= (uint16_t)((rx_freq_in_khz - (rx_bandwidth_in_khz + 1)/2 + 50) / 100);
    uint16_t				high_freq_dMHz 	= (uint16_t)((rx_freq_in_khz + (rx_bandwidth_in_khz + 1)/2 + 50) / 100);
    int 					site_selector;
//	duplexor_direction_t	direction_selector;
	unsigned				min_centre_offset	= UINT_MAX;
	int 					best_selection		= NO_FILTER_SITE_AVAILABLE;
	//int						wideband_present	= FALSE;

    if (rx_freq_in_khz >= 6000000) {
    	return return_value;
    }


	printf("%s, no. of filter site %d, freq %u %u", __func__, no_of_filter_sites, rx_freq_in_khz, freq_dMHz);

	for (site_selector = 0; site_selector < no_of_filter_sites; site_selector++) {
        unsigned filterId = fittedRxFilterIds[site_selector];

        if (filterId >= rxFilterBandsLen) {
        	// Nothing sensible defined for this filter site
        	continue;
        } else {
        	// Get filter details for this filter site
        	RxFilterBand_t	const * rxFilterBand_ptr = &rxFilterBands[filterId];

        	if (rxFilterBand_ptr->band != filter_band) {
        		// filter band for this slot isn't what we need
        		continue;
        	} else {
        		// Filter band matches, but we need to check the direction
        		uint16_t test_mask = (*duplexor_direction_ptr == DD_UPLINK) ? UPLINK_DIR_MASK : DOWNLINK_DIR_MASK;

            	if ((rxFilterBand_ptr->direction_mask & test_mask) == 0) {
            		// Filter does not have the direction we need.
            		continue;
            	} else {
            		// The filter site has the filter we need, but we could have more than one filter for the band, and the freq may not be in the passband of this one,
            		// or it could be in the passband of both so we need to chose between them
					uint16_t *duplexor_filters_branch_ptr = (*duplexor_direction_ptr == DD_UPLINK) ?
							(uint16_t *)rxFilterBand_ptr->uplink_branch :
							(uint16_t *)rxFilterBand_ptr->downlink_branch;

					if ((duplexor_filters_branch_ptr[LOW_FREQ] <= low_freq_dMHz) && (high_freq_dMHz <= duplexor_filters_branch_ptr[HIGH_FREQ])) {
						// channel centre lies within the passband of the filter
						unsigned band_centre = (duplexor_filters_branch_ptr[LOW_FREQ] + duplexor_filters_branch_ptr[HIGH_FREQ])/2;
						unsigned centre_offset = (freq_dMHz >= band_centre ? freq_dMHz - band_centre : band_centre - freq_dMHz);

						if ((centre_offset < min_centre_offset) && (filterId != WIDEBAND_FILTER_ID)) {
							// Use the filter where the wanted frequency is closest to the centre of the passband
							// Ignore the wideband option here, we might be closer to the middle of that than a proper filter but would use the
							// later choice in preference
//							printf("%s, %d, %u %d - New Min %d", __func__, site_selector, filterId, direction_selector, centre_offset);
							printf("%s, %d, %u - New Min %d", __func__, site_selector, filterId, centre_offset);
							min_centre_offset = centre_offset;
							best_selection = site_selector;
							*extra_data_ptr = rxFilterBand_ptr->extra_data;
						}
					}
            	}
        	}
        }
	}
	if (best_selection == NO_FILTER_SITE_AVAILABLE) {
		int selection_value = select_rx_filter_site_from_channel_centre_freq(	fittedRxFilterIds,
				no_of_filter_sites,
				rx_freq_in_khz,
				rx_bandwidth_in_khz,
				duplexor_direction_ptr,
				extra_data_ptr);;

		// See if the frequency is covered by another filter.
		printf("%s, Band Specific Hunt Failed Try Freq Hunt", __func__);

		*duplexor_direction_ptr = test_and_swap_direction(*extra_data_ptr, *duplexor_direction_ptr);
		return selection_value;
	} else {
		*duplexor_direction_ptr = test_and_swap_direction(*extra_data_ptr, *duplexor_direction_ptr);
		return best_selection;
	}
}

static int get_filter_limit(int filter_site, duplexor_direction_t direction_selector, int low_limit)
{
	int return_freq_dMHz = 0;
	int index = (low_limit) ? 0 : 1;


	if ((filter_site < 0) || (filter_site >= rxFilterBandsLen)) {
		return return_freq_dMHz;
	}

	switch (direction_selector) {
		case DD_UPLINK:
			return_freq_dMHz = rxFilterBands[filter_site].uplink_branch[index];
			break;

		case DD_DOWNLINK:
			return_freq_dMHz = rxFilterBands[filter_site].downlink_branch[index];
			break;

		default:
			// presume that this is a single filter rather than a duplexor so search for the non-zero values
			return_freq_dMHz = rxFilterBands[filter_site].uplink_branch[index];
			if (return_freq_dMHz == 0) {
				return_freq_dMHz = rxFilterBands[filter_site].downlink_branch[index];
			}
			break;
	}

	return return_freq_dMHz;
}

int get_filter_low_limit(int filter_site, duplexor_direction_t direction_selector)
{
	int return_value = get_filter_limit(filter_site, direction_selector, TRUE);

	printf("%s, filter site %d, duplexor direction %d, freq limit %d", __func__, filter_site, direction_selector, return_value);
	return return_value;
}

int get_filter_high_limit(int filter_site, duplexor_direction_t direction_selector)
{
	int return_value = get_filter_limit(filter_site, direction_selector, FALSE);

	printf("%s, filter site %d, duplexor direction %d, freq limit %d", __func__, filter_site, direction_selector, return_value);
	return return_value;
}

int get_ladon_filter_id(int filter_site)
{
	if ((filter_site < 0) || (filter_site > 0)) {
		return -1;
	} else {
		return rxFilterBands[filter_site].ladonId;
	}
}
