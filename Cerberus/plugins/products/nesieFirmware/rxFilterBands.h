#if !defined rxFilterBands_included
#define rxFilterBands_included

#include <stdint.h>
#include <limits.h>

typedef enum {
	DD_UNKNOWN	= -1,
	DD_UPLINK	= 0,
	DD_DOWNLINK	= 1,
	DD_MAX_NO	= 2
} duplexor_direction_t;

#define	LOW_FREQ	0
#define	HIGH_FREQ	1

typedef uint16_t filter_freqs_t[2];

typedef enum {
	// First Batch Follow Default Classic NESIE Band Defns
	BAND_FILTER_CDMA450		=	0,
	BAND_FILTER_IDEN		=	2,
	BAND_FILTER_GSM850		=	4,
	BAND_FILTER_EGSM900		=	6,
	BAND_FILTER_DCS1800		=	8,
	BAND_FILTER_PCS1900		=	10,
	BAND_FILTER_3GBAND1		=	12,
	BAND_FILTER_EMPTY		=	14,

	// Next Batch New Filters available on Default Covert,
	// Also on Modified Classic
	BAND_FILTER_LTE7		=	16,
	BAND_FILTER_LTE20		=	18,

	// Next Batch Extra Available on Modified Covert
	BAND_FILTER_LTE28		=	20,
	BAND_FILTER_LTE12		=	22,
	BAND_FILTER_LTE13		=	24,
	BAND_FILTER_LTE17		=	26,

	// TDD on Tactical
	BAND_FILTER_LTE40		=	28,
	BAND_FILTER_LTE38		=	30,
	BAND_FILTER_LTE41		=	32,

	// Additional TDD Tactical
	BAND_FILTER_LTE25		=	34,
	BAND_FILTER_LTE26		=	36,
	BAND_FILTER_LTE71		=	38,
	BAND_FILTER_N77 		=	40,

        // N.B. see also MAX_LTE_BAND below.

	// Generic
	BAND_FILTER_WIDE		=	1000,
	BAND_FILTER_ERROR		=	-1,
	BAND_ID_NONE			= 	INT_MAX

} band_filter_t;

band_filter_t _3gppToNesieBandFilterNumber(unsigned _3gppBandNumber);

#define UPLINK_DIR_MASK		(1)
#define DOWNLINK_DIR_MASK	(2)
#define BOTH_DIR_MASK		(UPLINK_DIR_MASK | DOWNLINK_DIR_MASK)

typedef enum {
	COVERT872CALDATALOOKUP_NO_LOOKUP	= -1,
	COVERT872CALDATALOOKUP_LTE_7		= 0,
	COVERT872CALDATALOOKUP_DCS1800,
	COVERT872CALDATALOOKUP_PCS1900,
	COVERT872CALDATALOOKUP_UMTS_1,
	COVERT872CALDATALOOKUP_GSM850,
	COVERT872CALDATALOOKUP_EGSM900,
	COVERT872CALDATALOOKUP_LTE_20,
	COVERT872CALDATALOOKUP_WIDEBAND,
	COVERT872CALDATALOOKUP_LTE_12,
	COVERT872CALDATALOOKUP_LTE_13,
	COVERT872CALDATALOOKUP_LTE_28A,
	COVERT872CALDATALOOKUP_LTE_28B,
	COVERT872CALDATALOOKUP_LTE_40,

	COVERT872CALDATALOOKUP_NO_OF_ENTRIES
} Covert872CalDataLookup_t;

typedef struct {
	filter_freqs_t				uplink_branch;
	filter_freqs_t				downlink_branch;
	uint16_t					direction_mask;
	uint16_t 					ladonId;
	band_filter_t				band;
	int8_t						lte_band;
	uint8_t						filter_no;
	uint8_t						no_of_filters_per_band;
	uint8_t						extra_data;
	Covert872CalDataLookup_t	covert872_caldata_lookup;
} RxFilterBand_t;

#define EXTRA_DATA_FORREV_MASK				1
#define EXTRA_DATA_SWAP_FOR_AND_REV_MASK	2

#ifdef TACTICAL_NESIE_HW
typedef RxFilterBand_t TxFilterBand_t;			// Reuse for Tx for Tactical
#define txFilterBands rxFilterBands
#endif

extern RxFilterBand_t const rxFilterBands[];
extern unsigned const rxFilterBandsLen;

#define NO_FILTER_SITE_AVAILABLE	-1
#define NOT_FITTED_FILTER_ID		0
#define WIDEBAND_FILTER_ID			1
#define BOTTOM_850UL_FILTER_ID		20

#define FILTER_BLOCK0_START			0		// generics: Empty and Wideband
#define FILTER_BLOCK1_START			2		// Classic NESIE Standard Filters
#define FILTER_BLOCK2_START			16		// Classic NESIE Additional LTE Filters		7/20
#define FILTER_BLOCK3_START			21		// Covert NESIE Standard Filters
#define FILTER_BLOCK4_START			28		// Covert NESIE Additional LTE Filters 1, 	28A/B
#define FILTER_BLOCK5_START			30		// Flight/NESIE2 Standard Filters
#define FILTER_BLOCK6_START			44		// Covert NESIE Additional LTE Filters 2 	12/13/17
#define FILTER_BLOCK7_START			47		// Tactical NESIE Standard Filters
#define FILTER_BLOCK8_START			54		// Covert NESIE Additional LTE Filters 3	13 "Reversed"
#define FILTER_BLOCK9_START			55		// Tactical NESIE Additional LTE Filters 1	40
#define FILTER_BLOCK10_START		56		// Covert NESIE Additional LTE Filters 4	40/28 "Reversed"

#define	MAX_LTE_BAND				77


#ifdef NESIE_HW

#define NO_OF_RX_FILTER_SITES			14
#define MAX_NO_OF_RX_FILTER_SITES		NO_OF_RX_FILTER_SITES

#elif defined(MINI_NESIE_HW)

#define NO_OF_RX_FILTER_SITES_784		8
#define NO_OF_RX_FILTER_SITES_872		11 // This RF Board has 10 "Duplexor" Slots rather than the standard 8 + a non-standard wideband connection.
#define MAX_NO_OF_RX_FILTER_SITES		NO_OF_RX_FILTER_SITES_872
int SM872_query(void);
#define NO_OF_RX_FILTER_SITES			((SM872_query()) ? NO_OF_RX_FILTER_SITES_872 : NO_OF_RX_FILTER_SITES_784)

#elif defined(NESIE2_HW)

#define NO_OF_RX_FILTER_SITES			16
#define MAX_NO_OF_RX_FILTER_SITES		NO_OF_RX_FILTER_SITES

#elif defined(TACTICAL_NESIE_HW)
#define NO_OF_RX_FILTER_SITES			12
#define NO_OF_TX_FILTER_SITES			12
#define MAX_NO_OF_RX_FILTER_SITES		NO_OF_RX_FILTER_SITES
#else
#endif

int select_rx_filter_site_from_channel_centre_freq(	uint8_t 				 fittedRxFilterIds[],
													int 					 no_of_filter_sites,
													uint32_t				 rx_freq_in_khz,
													uint32_t				 rx_bandwidth_in_khz,
													duplexor_direction_t	*duplexor_direction_ptr,
													uint8_t					*extra_data_ptr
		);
int get_filter_low_limit(int filter_site, duplexor_direction_t direction_selector);
int get_filter_high_limit(int filter_site, duplexor_direction_t direction_selector);

int select_rx_filter_site_from_band_and_channel_centre_freq(	uint8_t 				 fittedRxFilterIds[],
																int 					 no_of_filter_sites,
																uint32_t				 rx_freq_in_khz,
																uint32_t				 rx_bandwidth_in_khz,
																band_filter_t			 filter_band,
																duplexor_direction_t	*duplexor_direction_ptr,
																uint8_t					*extra_data_ptr

	);


#endif //#if !defined rxFilterBands_included

