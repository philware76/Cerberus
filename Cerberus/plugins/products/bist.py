import logging
import time
from typing import Optional

from Cerberus.telnetClient import TelnetClient, TelnetError


class Bist:
    """
    BIST interface using TelnetClient.
    Blocking / synchronous: commands wait up to the TelnetClient timeout (default 120s).
    """

    def __init__(self):
        logging.debug("__init__")
        self._client: TelnetClient | None = None

    def initComms(self, host: str, port: int = 51234, timeout: float = 120.0):
        self._client = TelnetClient(host, port, timeout=timeout)

    # Connection lifecycle -------------------------------------------------------------

    def openBIST(self) -> None:
        if self._client is None:
            raise TelnetError("initComms has not been configured.")

        self._client.open()

    def closeBIST(self) -> None:
        if self._client is None:
            return

        self._client.close()

    def is_open(self) -> bool:
        if self._client is None:
            raise TelnetError("Must open the BIST communication first")

        return self._client.is_open()

    # Low-level helpers ----------------------------------------------------------------
    def _send(self, cmd: str) -> None:
        if self._client is None or not self._client.is_open():
            raise TelnetError("Must open the BIST communication first")

        self._client.send(cmd)

    def _query(self, cmd: str) -> str:
        if self._client is None or not self._client.is_open():
            raise TelnetError("Must open the BIST communication first")

        resp = self._client.query(cmd)
        return resp

    # Core command wrappers ------------------------------------------------------------

    def tx_enable(self):
        logging.debug('Switching Test Unit TX ON')
        self._query('TX:ENAB')

    def get_tx_enable(self):
        logging.debug('Querying PA')
        return self._query('TX:ENAB?')

    def pa_enable(self, *, freq=None, pa=None):
        if pa is not None:
            freq = None
        selected_pa: Optional[str] = None
        if freq is not None:
            if freq < 1000:
                selected_pa = 'PA_LOW'
            elif 1000 < freq < 3000:
                selected_pa = 'PA_HIGH'
            elif freq >= 3000:
                selected_pa = 'PA_3GHZ'
        if pa == 'low':
            selected_pa = 'PA_LOW'
        elif pa == 'high':
            selected_pa = 'PA_HIGH'
        elif pa == '3ghz':
            selected_pa = 'PA_3GHZ'
        if selected_pa:
            logging.debug(f'Switching To {selected_pa} Path')
            self._query(f'TX:PAPATH {selected_pa}')
            logging.debug(f'Switching {selected_pa} ON')
            self._query(f'TX:PAEN {selected_pa}')
            time.sleep(0.2)

    def get_pa_path(self):
        logging.debug('Querying PA Path...')
        return self._query('TX:PAPATH?')

    def tx_disable(self):
        logging.debug('Switching Test Unit TX OFF')
        self._query('TX:DISA')

    def pa_disable(self):
        logging.debug('Switching PA OFF')
        self._query('TX:PAEN PA_OFF')
        self._query('TX:PAPATH PA_OFF')

    def pa_power(self, *, freq=None):
        logging.debug('Checking On Board Power Detector')
        if freq is None:
            return self._query('TX:PAPWR? RAW')
        return self._query(f'TX:PAPWR? {int(freq)}')

    def set_attn(self, attn_lvl):
        logging.debug(f'Setting Test Unit Attenuation: {attn_lvl}')
        self._query(f'TX:ATTN {attn_lvl}')

    def get_attn(self):
        return self._query('TX:ATTN?')

    def tx_freq(self, freq):
        freq_sent = int(freq * 1e6)
        logging.debug(f'Setting Test Unit Frequency: {freq}MHz')
        self._query(f'TX:FREQ {freq_sent}')

    def get_tx_freq(self):
        return self._query('TX:FREQ?')

    def ts_enable(self):
        logging.debug('Switching Test Unit TX Test Signal ON')
        self._query('TX:TS:ENAB')

    def ts_disable(self):
        logging.debug('Switching Test Unit TX Test Signal OFF')
        self._query('TX:TS:DISA')

    def get_ts_freq(self):
        return self._query('TX:TS:FREQ?')

    def ts_freq(self, freq):
        freq_sent = int(freq * 1e6)
        logging.debug(f'Setting Test Source Frequency: {freq}MHz')
        self._query(f'TX:TS:FREQ {freq_sent}')

    def rx_freq(self):
        return self._query('RX:FREQ?')

    def set_rx_freq(self, freq):
        freq_sent = int(freq * 1e6)
        logging.debug(f'Setting Test Unit RX Frequency: {freq}MHz')
        self._query(f'RX:FREQ {freq_sent}')

    def get_rx_band(self):
        return self._query('RX:BAND?')

    def set_rx_band(self, band, FWDorREV):
        if FWDorREV not in ['FWD', 'REV']:
            logging.debug('Missing Argument: Select FWD or REV.')
            return
        logging.debug(f'Setting Test Unit RX Band: {FWDorREV} {band}')
        self._query(f'RX:BAND {FWDorREV} {band}')

    def rx_gain(self):
        return self._query('RX:GAIN?')

    def set_rx_gain(self, gain):
        logging.debug(f'Setting Test Unit RX GAIN: {gain}')
        self._query(f'RX:GAIN {gain}')

    def get_rx_bw(self):
        return self._query('RX:BW?')

    def set_rx_bw(self, bw):
        bandwidth = int(bw * 1e6)
        logging.debug(f'Setting Test Unit RX BW: {bandwidth}')
        self._query(f'RX:BW {bandwidth}')

    def tx_bw(self):
        return self._query('TX:BW?')

    def set_tx_bw(self, bw):
        bandwidth = int(bw * 1e6)
        logging.debug(f'Setting Test Unit TX BW: {bandwidth}')
        self._query(f'TX:BW {bandwidth}')

    def rx_capt(self, *, smpf_low=False, smpf_high=False, XVIk=False):
        logging.debug('Initiating Unit RX Capture')
        cpt_opt = None
        if smpf_low and not smpf_high and not XVIk:
            logging.debug('Setting Sample Frequency to 3.2768 MHz')
            cpt_opt = '3M2768'
        elif smpf_high and not smpf_low and not XVIk:
            logging.debug('Setting Sample Frequency to 30.72 MHz')
            cpt_opt = '30M72'
        elif XVIk and not smpf_high and not smpf_low:
            logging.debug('Initiating Capture')
            cpt_opt = '16K'
        else:
            logging.debug('Capture Option Needs selecting (High/Low/16K)')
        if cpt_opt is None:
            return
        if XVIk:
            return self._query(f'RX:CAPT? {cpt_opt}')
        self._query(f'RX:CAPT? {cpt_opt}')
        return None

    def get_rssi(self, type, *, freq=None):
        if type in ['RF', 'IF', 'BB', 'OF']:
            parts = self._query(f'RX:RSSI? {type}').split()
            return parts[2] if len(parts) >= 3 else ''
        if type == 'INPUT' and freq is not None:
            parts = self._query(f'RX:RSSI? {type} {freq}').split()
            return parts[2] if len(parts) >= 3 else ''
        logging.debug('Invalid Type Selection or Frequency not Set')
        return ''

    def get_duplexer(self, TXorRX):
        if TXorRX not in ['RX', 'TX']:
            logging.debug('TXorRX Selection Invalid')
            return ''
        logging.debug('Querying Duplexer...')
        return self._query(f'{TXorRX}:DUP?')

    def set_duplexer(self, band_name, *, TXorRX=None):
        if TXorRX not in ['TX', 'RX']:
            logging.debug('Select Transmit or Receive Path (TX/RX) ONLY')
            return
        names = ['LTE_7', 'LTE_20', 'GSM850', 'EGSM900', 'DCS1800', 'PCS1900', 'UMTS_1', 'SPARE', 'SPARE2', 'SPARE3', 'SPARE4', 'SPARE5']
        try:
            slot_num = names.index(band_name)
        except ValueError:
            logging.debug(f'Band name {band_name} not recognised')
            return
        if TXorRX == 'TX':
            f_paths = ['DUP100', 'DUP101', 'DUP102', 'FIL100', 'FIL101', 'FIL102', 'DUP103', 'DUP104', 'DUP105', 'DUP106', 'DUP107', 'DUP108']
        else:  # RX
            f_paths = ['DUP300', 'DUP301', 'DUP302', 'FIL300', 'FIL301', 'FIL302', 'DUP303', 'DUP304', 'DUP305', 'DUP306', 'DUP307', 'DUP308']
        selected_path = f_paths[slot_num]
        logging.debug(f'Setting Duplexer Path To: {selected_path}')
        self._query(f'{TXorRX}:DUP {selected_path}')

    def set_ocxo(self, ocxo_setting):
        value_sent = int(ocxo_setting)
        logging.debug(f'Setting OCXO to: {value_sent}')
        self._query(f'OCXO {value_sent}')

    def get_ocxo(self):
        logging.debug('Querying OCXO...')
        return self._query('OCXO?')

    def get_temps(self):
        logging.debug('Checking Unit Temperature...')
        da_temp_raw = self._query('DA:TEMP?')

        def _flt(s: str) -> float:
            num = ''.join(c for c in s if c.isdigit() or c == '.')
            return float(num) if num else float('nan')

        da_temp = _flt(da_temp_raw)
        rf_temp = _flt(self._query('ENG:TEMP?'))
        pa_temp = _flt(self._query('TX:PATEMP?'))
        rfmb_temp = _flt(self._query('ENG:TEMP? MB'))

        logging.debug(f'DA:{da_temp} RF:{rf_temp} PA:{pa_temp} MB:{rfmb_temp}')
        return da_temp, rf_temp, pa_temp, rfmb_temp

    def get_tx_fwd_rev(self):
        logging.debug('Querying TX Link Direction')
        return self._query('TX:FORREV?')

    def set_tx_fwd_rev(self, band, FWDorREV):
        if FWDorREV not in ['FWD', 'REV']:
            logging.debug('Select TX Link Direction (FWD/REV)')
            return

        logging.debug(f'Setting TX Link Direction To {FWDorREV}')

        # Logic preserved from legacy implementation
        special = ['0x30', '0x37', '0x3d', '0x1c', '0x3f', '0x39']
        if FWDorREV == 'FWD':
            cmd = 'TX:FORREV SET' if band in special else 'TX:FORREV CLEAR'
        else:  # REV
            cmd = 'TX:FORREV CLEAR' if band in special else 'TX:FORREV SET'

        self._query(cmd)

    def get_rx_fwd_rev(self):
        logging.debug('Querying RX Link Direction')
        return self._query('RX:FORREV?')

    def set_rx_fwd_rev(self, band, FWDorREV):
        if FWDorREV not in ['FWD', 'REV']:
            logging.debug('Select RX Link Direction (FWD/REV)')
            return
        logging.debug(f'Setting RX Link Direction To {FWDorREV}')
        special = ['0x30', '0x37', '0x3d', '0x1c', '0x3f', '0x39']
        if FWDorREV == 'FWD':
            cmd = 'RX:FORREV SET' if band in special else 'RX:FORREV CLEAR'
        else:  # REV
            cmd = 'RX:FORREV CLEAR' if band in special else 'RX:FORREV SET'
        self._query(cmd)

    def set_rx_input(self, input):
        if input not in ['ANT', 'DAISY', 'LNA', 'BYPASS']:
            logging.debug('Select RX Input: ANT/DAISY/LNA/BYPASS')
            return
        target = 'ANT' if input in ['ANT', 'LNA'] else 'DAISY'
        logging.debug(f'Setting RX Input To {target}')
        self._query(f'RX:INPUT {target}')

    def get_lna_version(self):
        logging.debug('Querying LNA Version')
        return self._query('RX:HWTYPE?')

    def get_rx_offset(self, freq):
        logging.debug('Querying RX:OFFSET for current band')
        test_freq = f'{freq:.0f}'
        return self._query(f'RX:OFFSET? {test_freq}')

    def get_rx_input(self):
        logging.debug('Querying RX Input')
        return self._query('RX:INPUT?')

    def bist_mode_enable(self):
        logging.debug('Setting BIST MODE ON')
        self._query('APP:BIST_MODE_ENABLE')

    def bist_mode_disable(self):
        logging.debug('Setting BIST MODE OFF')
        self._query('APP:BIST_MODE_DISABLE')

    def gsm_app_ctrl(self, ARFCN, power, on_off, *, delta=None):
        if not 0 <= power <= 31:
            logging.error(f'Power Level {power} out of Range (MAX 31)')
            return
        if isinstance(delta, int):
            self._query(f'APP:PE_DELTA {delta}')
        if on_off in ['on', 'ON', 1]:
            self._query(f'APP:PE_START {ARFCN} {power}')
        elif on_off in ['off', 'OFF', 0]:
            self._query('APP:PE_STOP')
        else:
            logging.debug(f'ON/OFF command: {on_off} NOT understood')

    def umts_output(self, on_off, *, band=0):
        if on_off in ['on', 'ON', 1]:
            if band not in [1, 8]:
                logging.debug('Band command not recognised')
                return
            band_details = [21400, 11] if band == 1 else [9420, 11]
            logging.debug('Setting up and turning on a UMTS waveform')
            self._query('APP:NESIERF:OFF')
            time.sleep(6)
            self._query('SCPI:*RST')
            self._query('SCPI:TRX:STOP')
            for i in range(1, 5):
                self._query(f'SCPI:TX:CONF:BLOCKINGCELL {i},0,0')
            self._query(f'SCPI:TX:CONF:MODE {band_details[1]}')
            self._query(f'SCPI:TX:CONF:FREQ {band_details[0]}')
            self._query('SCPI:TX:CONF:PSCHGAIN 0')
            self._query('SCPI:TX:CONF:SSCHGAIN 0')
            self._query('SCPI:TX:CONF:PCCPCHGAIN 0')
            self._query('SCPI:TX:CONF:SCCPCHGAIN 0')
            self._query('SCPI:TX:CONF:AICHGAIN 0')
            self._query('SCPI:TX:CONF:CPICHGAIN 8000')
            self._query('SCPI:TX:CONF:ATTN 2')
            self._query('SCPI:TX:CONF:LIMITERGAIN 0')
            self._query('SCPI:TRX:CONF:PRIMARYSCRAMBLINGCODE 17')
            self._query('SCPI:TRX:START')
        else:
            logging.debug('Switching off UMTS waveform')
            self._query('SCPI:TRX:STOP')
            for i in range(1, 5):
                self._query(f'SCPI:TX:CONF:BLOCKINGCELL {i},0,0')

    def tx_lte_start(self, freq):
        logging.debug('Starting LTE TX')
        deci_MHz = int(round(10 * freq, 0))
        limiter_gain = 0
        self._query('APP:NESIERF:CLOSEDLOOPPWRCTL ENABLE')
        self._query(f'APP:NESIERF:LIMITER {limiter_gain}')
        self._query('APP:NESIERF:ATTN 15 0')
        self._query(f'APP:NESIERF:TX {deci_MHz} 400 NOHUP')
        time.sleep(10)

    def tx_lte_stop(self):
        logging.debug('Stopping LTE TX')
        self._query('APP:NESIERF:OFF')
