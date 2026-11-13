"""Actual CICIDS2017 (GeneratedLabelledFlows / TrafficLabelling) schema and feature dictionary."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    group: str
    unit: str
    description: str


_F = FeatureSpec

# Definitions follow the CICFlowMeter output. "Fwd" = direction of the first packet of the flow,
# "Bwd" = the opposite direction. Neither means "to the server" or "from the server".
NUMERIC_FEATURES: tuple[FeatureSpec, ...] = (
    _F("Flow Duration", "duration", "мкс", "Тривалість потоку"),
    _F("Total Fwd Packets", "volume", "пакети", "Кількість пакетів у прямому напрямку"),
    _F("Total Backward Packets", "volume", "пакети", "Кількість пакетів у зворотному напрямку"),
    _F("Total Length of Fwd Packets", "volume", "байти", "Сумарний розмір пакетів у прямому напрямку"),
    _F("Total Length of Bwd Packets", "volume", "байти", "Сумарний розмір пакетів у зворотному напрямку"),
    _F("Fwd Packet Length Max", "packet_length", "байти", "Максимальний розмір пакета у прямому напрямку"),
    _F("Fwd Packet Length Min", "packet_length", "байти", "Мінімальний розмір пакета у прямому напрямку"),
    _F("Fwd Packet Length Mean", "packet_length", "байти", "Середній розмір пакета у прямому напрямку"),
    _F("Fwd Packet Length Std", "packet_length", "байти", "Стандартне відхилення розміру пакета у прямому напрямку"),
    _F("Bwd Packet Length Max", "packet_length", "байти", "Максимальний розмір пакета у зворотному напрямку"),
    _F("Bwd Packet Length Min", "packet_length", "байти", "Мінімальний розмір пакета у зворотному напрямку"),
    _F("Bwd Packet Length Mean", "packet_length", "байти", "Середній розмір пакета у зворотному напрямку"),
    _F("Bwd Packet Length Std", "packet_length", "байти", "Стандартне відхилення розміру пакета у зворотному напрямку"),
    _F("Flow Bytes/s", "rate", "байт/с", "Інтенсивність потоку в байтах за секунду"),
    _F("Flow Packets/s", "rate", "пакет/с", "Інтенсивність потоку в пакетах за секунду"),
    _F("Flow IAT Mean", "iat", "мкс", "Середній інтервал між пакетами потоку"),
    _F("Flow IAT Std", "iat", "мкс", "Стандартне відхилення інтервалу між пакетами потоку"),
    _F("Flow IAT Max", "iat", "мкс", "Максимальний інтервал між пакетами потоку"),
    _F("Flow IAT Min", "iat", "мкс", "Мінімальний інтервал між пакетами потоку"),
    _F("Fwd IAT Total", "iat", "мкс", "Сума інтервалів між пакетами прямого напрямку"),
    _F("Fwd IAT Mean", "iat", "мкс", "Середній інтервал між пакетами прямого напрямку"),
    _F("Fwd IAT Std", "iat", "мкс", "Стандартне відхилення інтервалу прямого напрямку"),
    _F("Fwd IAT Max", "iat", "мкс", "Максимальний інтервал прямого напрямку"),
    _F("Fwd IAT Min", "iat", "мкс", "Мінімальний інтервал прямого напрямку"),
    _F("Bwd IAT Total", "iat", "мкс", "Сума інтервалів між пакетами зворотного напрямку"),
    _F("Bwd IAT Mean", "iat", "мкс", "Середній інтервал між пакетами зворотного напрямку"),
    _F("Bwd IAT Std", "iat", "мкс", "Стандартне відхилення інтервалу зворотного напрямку"),
    _F("Bwd IAT Max", "iat", "мкс", "Максимальний інтервал зворотного напрямку"),
    _F("Bwd IAT Min", "iat", "мкс", "Мінімальний інтервал зворотного напрямку"),
    _F("Fwd PSH Flags", "flags", "кількість", "Кількість прапорців PSH у прямому напрямку"),
    _F("Bwd PSH Flags", "flags", "кількість", "Кількість прапорців PSH у зворотному напрямку"),
    _F("Fwd URG Flags", "flags", "кількість", "Кількість прапорців URG у прямому напрямку"),
    _F("Bwd URG Flags", "flags", "кількість", "Кількість прапорців URG у зворотному напрямку"),
    _F("Fwd Header Length", "header", "байти", "Сумарний розмір заголовків прямого напрямку"),
    _F("Bwd Header Length", "header", "байти", "Сумарний розмір заголовків зворотного напрямку"),
    _F("Fwd Packets/s", "rate", "пакет/с", "Інтенсивність пакетів прямого напрямку"),
    _F("Bwd Packets/s", "rate", "пакет/с", "Інтенсивність пакетів зворотного напрямку"),
    _F("Min Packet Length", "packet_length", "байти", "Мінімальний розмір пакета потоку"),
    _F("Max Packet Length", "packet_length", "байти", "Максимальний розмір пакета потоку"),
    _F("Packet Length Mean", "packet_length", "байти", "Середній розмір пакета потоку"),
    _F("Packet Length Std", "packet_length", "байти", "Стандартне відхилення розміру пакета потоку"),
    _F("Packet Length Variance", "packet_length", "байти²", "Дисперсія розміру пакета потоку"),
    _F("FIN Flag Count", "flags", "кількість", "Кількість пакетів із прапорцем FIN"),
    _F("SYN Flag Count", "flags", "кількість", "Кількість пакетів із прапорцем SYN"),
    _F("RST Flag Count", "flags", "кількість", "Кількість пакетів із прапорцем RST"),
    _F("PSH Flag Count", "flags", "кількість", "Кількість пакетів із прапорцем PSH"),
    _F("ACK Flag Count", "flags", "кількість", "Кількість пакетів із прапорцем ACK"),
    _F("URG Flag Count", "flags", "кількість", "Кількість пакетів із прапорцем URG"),
    _F("CWE Flag Count", "flags", "кількість", "Кількість пакетів із прапорцем CWR"),
    _F("ECE Flag Count", "flags", "кількість", "Кількість пакетів із прапорцем ECE"),
    _F("Down/Up Ratio", "rate", "відношення", "Відношення кількості пакетів зворотного напрямку до прямого (за пакетами, не за байтами)"),
    _F("Average Packet Size", "packet_length", "байти", "Середній розмір пакета"),
    _F("Avg Fwd Segment Size", "packet_length", "байти", "Середній розмір сегмента прямого напрямку"),
    _F("Avg Bwd Segment Size", "packet_length", "байти", "Середній розмір сегмента зворотного напрямку"),
    _F("Fwd Avg Bytes/Bulk", "bulk", "байти", "Середня кількість байтів у пакетному блоці прямого напрямку"),
    _F("Fwd Avg Packets/Bulk", "bulk", "пакети", "Середня кількість пакетів у блоці прямого напрямку"),
    _F("Fwd Avg Bulk Rate", "bulk", "байт/с", "Середня швидкість блоку прямого напрямку"),
    _F("Bwd Avg Bytes/Bulk", "bulk", "байти", "Середня кількість байтів у блоці зворотного напрямку"),
    _F("Bwd Avg Packets/Bulk", "bulk", "пакети", "Середня кількість пакетів у блоці зворотного напрямку"),
    _F("Bwd Avg Bulk Rate", "bulk", "байт/с", "Середня швидкість блоку зворотного напрямку"),
    _F("Subflow Fwd Packets", "subflow", "пакети", "Середня кількість пакетів підпотоку прямого напрямку"),
    _F("Subflow Fwd Bytes", "subflow", "байти", "Середня кількість байтів підпотоку прямого напрямку"),
    _F("Subflow Bwd Packets", "subflow", "пакети", "Середня кількість пакетів підпотоку зворотного напрямку"),
    _F("Subflow Bwd Bytes", "subflow", "байти", "Середня кількість байтів підпотоку зворотного напрямку"),
    _F("Init_Win_bytes_forward", "tcp_window", "байти", "Початкове вікно TCP прямого напрямку; -1 означає, що значення відсутнє"),
    _F("Init_Win_bytes_backward", "tcp_window", "байти", "Початкове вікно TCP зворотного напрямку; -1 означає, що значення відсутнє"),
    _F("act_data_pkt_fwd", "tcp_window", "пакети", "Кількість пакетів прямого напрямку з ненульовим TCP-корисним навантаженням"),
    _F("min_seg_size_forward", "tcp_window", "байти", "Мінімальний розмір сегмента прямого напрямку"),
    _F("Active Mean", "active_idle", "мкс", "Середній час активності потоку"),
    _F("Active Std", "active_idle", "мкс", "Стандартне відхилення часу активності"),
    _F("Active Max", "active_idle", "мкс", "Максимальний час активності"),
    _F("Active Min", "active_idle", "мкс", "Мінімальний час активності"),
    _F("Idle Mean", "active_idle", "мкс", "Середній час простою потоку"),
    _F("Idle Std", "active_idle", "мкс", "Стандартне відхилення часу простою"),
    _F("Idle Max", "active_idle", "мкс", "Максимальний час простою"),
    _F("Idle Min", "active_idle", "мкс", "Мінімальний час простою"),
)

PROTOCOL_COLUMN = "Protocol"
PROTOCOL_SPEC = _F(PROTOCOL_COLUMN, "protocol", "номер IP-протоколу",
                   "Подається у модель двома бінарними ознаками: protocol_tcp (6) і protocol_udp (17)")

# Order of model inputs at the API and in the processed tables.
FEATURE_COLUMNS: tuple[str, ...] = (PROTOCOL_COLUMN, *(f.name for f in NUMERIC_FEATURES))

# Features where a negative value is a legitimate sentinel rather than a measurement error.
NEGATIVE_ALLOWED: frozenset[str] = frozenset({"Init_Win_bytes_forward", "Init_Win_bytes_backward"})

LABEL_COLUMN = "Label"
TIMESTAMP_COLUMN = "Timestamp"
DUPLICATE_COLUMN = "Fwd Header Length.1"
BENIGN_LABEL = "BENIGN"

# Metadata kept with each record for traceability, never passed to the model.
META_COLUMNS: tuple[str, ...] = ("Source IP", "Source Port", "Destination IP", "Destination Port")

EXCLUDED_COLUMNS: dict[str, str] = {
    "Flow ID": "Ідентифікатор потоку, похідний від IP та портів; не є поведінковою ознакою",
    "Source IP": "Ідентифікатор конкретного вузла стенду; ризик запам'ятовування адрес атакувальників",
    "Destination IP": "Ідентифікатор конкретного вузла стенду; ризик запам'ятовування адрес жертв",
    "Source Port": "Ефемерний номер порту; числова величина не має порядкового змісту",
    "Destination Port": "Категоріальний номер сервісу; числова величина не має порядкового змісту, ризик прив'язки до портів стенду",
    "Timestamp": "Використовується для часу події, але не як ознака: час доби пов'язаний із розкладом атак у стенді",
    DUPLICATE_COLUMN: "Точна копія Fwd Header Length (перевіряється під час завантаження)",
    LABEL_COLUMN: "Цільова мітка; використовується лише для поділу, вибору порога й оцінювання",
}

_names = [f.name for f in NUMERIC_FEATURES]
_duplicate_position = _names.index("Avg Bwd Segment Size") + 1

EXPECTED_COLUMNS: tuple[str, ...] = (
    "Flow ID", "Source IP", "Source Port", "Destination IP", "Destination Port", PROTOCOL_COLUMN,
    TIMESTAMP_COLUMN,
    *_names[:_duplicate_position],
    DUPLICATE_COLUMN,
    *_names[_duplicate_position:],
    LABEL_COLUMN,
)

# Files in capture order and their split. Monday contains only benign traffic.
FILE_SPLITS: tuple[tuple[str, str, str], ...] = (
    ("Monday-WorkingHours.pcap_ISCX.csv", "2017-07-03", "train"),
    ("Tuesday-WorkingHours.pcap_ISCX.csv", "2017-07-04", "validation"),
    ("Wednesday-workingHours.pcap_ISCX.csv", "2017-07-05", "validation"),
    ("Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv", "2017-07-06", "test"),
    ("Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv", "2017-07-06", "test"),
    ("Friday-WorkingHours-Morning.pcap_ISCX.csv", "2017-07-07", "test"),
    ("Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv", "2017-07-07", "test"),
    ("Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv", "2017-07-07", "test"),
)
SPLIT_ORDER: tuple[str, ...] = ("train", "validation", "test")

KNOWN_LABELS: frozenset[str] = frozenset({
    BENIGN_LABEL, "FTP-Patator", "SSH-Patator", "DoS Hulk", "DoS GoldenEye", "DoS slowloris",
    "DoS Slowhttptest", "Heartbleed", "Web Attack - Brute Force", "Web Attack - XSS",
    "Web Attack - Sql Injection", "Infiltration", "Bot", "PortScan", "DDoS",
})

# Verdict on every feature proposed in table 2.2 of the practice-report draft.
DRAFT_FEATURE_MAPPING: tuple[tuple[str, str, str, str], ...] = (
    ("request_rate", "Немає", "Flow Packets/s (лише наближено)",
     "У CICIDS2017 немає поняття запиту; є інтенсивність пакетів окремого потоку"),
    ("connection_count", "Немає", "—",
     "Набір містить по одному запису на потік; кількість з'єднань за вікно не реалізована"),
    ("src_bytes", "Частково", "Total Length of Fwd Packets",
     "Напрям визначено першим пакетом потоку, а не роллю сервера"),
    ("dst_bytes", "Частково", "Total Length of Bwd Packets",
     "Напрям визначено першим пакетом потоку, а не роллю сервера"),
    ("error_rate", "Немає", "—", "HTTP-коди відповідей у наборі відсутні"),
    ("avg_response_time", "Немає", "—",
     "Час відповіді прикладного рівня відсутній; Flow IAT є інтервалом між пакетами, а не часом відповіді"),
    ("unique_src_ips", "Немає", "—",
     "Source IP є, але агрегація за часовими вікнами не реалізована, а IP виключено з ознак"),
    ("protocol_type", "Так", "Protocol → protocol_tcp, protocol_udp", "Номер IP-протоколу, закодований бінарно"),
    ("status_code_group", "Немає", "—", "HTTP-коди відповідей у наборі відсутні"),
    ("traffic_ratio", "Частково", "Down/Up Ratio", "Відношення за кількістю пакетів, а не за обсягом"),
)
