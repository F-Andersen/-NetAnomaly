# Словник ознак CICIDS2017

Згенеровано з фактичного запуску `full_seed42` ([CSV](../reports/full_seed42/feature_dictionary.csv)). Джерело колонок: `GeneratedLabelledFlows.zip`, 85 колонок.

«Прямий» напрям (Fwd) задається першим пакетом потоку, «зворотний» (Bwd) — протилежний. Жоден із них не означає напрям «до сервера» чи «від сервера».

Вхід API містить 77 колонки. Після кодування `Protocol` двома бінарними ознаками й вилучення сталих колонок модель отримує 68 ознак.

## Використані ознаки

| № | Колонка CICIDS2017 | Група | Одиниця | Опис | Ознаки моделі |
| --- | --- | --- | --- | --- | --- |
| 1 | `Protocol` | protocol | номер IP-протоколу | Подається у модель двома бінарними ознаками: protocol_tcp (6) і protocol_udp (17) | protocol_tcp;protocol_udp |
| 2 | `Flow Duration` | duration | мкс | Тривалість потоку | Flow Duration |
| 3 | `Total Fwd Packets` | volume | пакети | Кількість пакетів у прямому напрямку | Total Fwd Packets |
| 4 | `Total Backward Packets` | volume | пакети | Кількість пакетів у зворотному напрямку | Total Backward Packets |
| 5 | `Total Length of Fwd Packets` | volume | байти | Сумарний розмір пакетів у прямому напрямку | Total Length of Fwd Packets |
| 6 | `Total Length of Bwd Packets` | volume | байти | Сумарний розмір пакетів у зворотному напрямку | Total Length of Bwd Packets |
| 7 | `Fwd Packet Length Max` | packet_length | байти | Максимальний розмір пакета у прямому напрямку | Fwd Packet Length Max |
| 8 | `Fwd Packet Length Min` | packet_length | байти | Мінімальний розмір пакета у прямому напрямку | Fwd Packet Length Min |
| 9 | `Fwd Packet Length Mean` | packet_length | байти | Середній розмір пакета у прямому напрямку | Fwd Packet Length Mean |
| 10 | `Fwd Packet Length Std` | packet_length | байти | Стандартне відхилення розміру пакета у прямому напрямку | Fwd Packet Length Std |
| 11 | `Bwd Packet Length Max` | packet_length | байти | Максимальний розмір пакета у зворотному напрямку | Bwd Packet Length Max |
| 12 | `Bwd Packet Length Min` | packet_length | байти | Мінімальний розмір пакета у зворотному напрямку | Bwd Packet Length Min |
| 13 | `Bwd Packet Length Mean` | packet_length | байти | Середній розмір пакета у зворотному напрямку | Bwd Packet Length Mean |
| 14 | `Bwd Packet Length Std` | packet_length | байти | Стандартне відхилення розміру пакета у зворотному напрямку | Bwd Packet Length Std |
| 15 | `Flow Bytes/s` | rate | байт/с | Інтенсивність потоку в байтах за секунду | Flow Bytes/s |
| 16 | `Flow Packets/s` | rate | пакет/с | Інтенсивність потоку в пакетах за секунду | Flow Packets/s |
| 17 | `Flow IAT Mean` | iat | мкс | Середній інтервал між пакетами потоку | Flow IAT Mean |
| 18 | `Flow IAT Std` | iat | мкс | Стандартне відхилення інтервалу між пакетами потоку | Flow IAT Std |
| 19 | `Flow IAT Max` | iat | мкс | Максимальний інтервал між пакетами потоку | Flow IAT Max |
| 20 | `Flow IAT Min` | iat | мкс | Мінімальний інтервал між пакетами потоку | Flow IAT Min |
| 21 | `Fwd IAT Total` | iat | мкс | Сума інтервалів між пакетами прямого напрямку | Fwd IAT Total |
| 22 | `Fwd IAT Mean` | iat | мкс | Середній інтервал між пакетами прямого напрямку | Fwd IAT Mean |
| 23 | `Fwd IAT Std` | iat | мкс | Стандартне відхилення інтервалу прямого напрямку | Fwd IAT Std |
| 24 | `Fwd IAT Max` | iat | мкс | Максимальний інтервал прямого напрямку | Fwd IAT Max |
| 25 | `Fwd IAT Min` | iat | мкс | Мінімальний інтервал прямого напрямку | Fwd IAT Min |
| 26 | `Bwd IAT Total` | iat | мкс | Сума інтервалів між пакетами зворотного напрямку | Bwd IAT Total |
| 27 | `Bwd IAT Mean` | iat | мкс | Середній інтервал між пакетами зворотного напрямку | Bwd IAT Mean |
| 28 | `Bwd IAT Std` | iat | мкс | Стандартне відхилення інтервалу зворотного напрямку | Bwd IAT Std |
| 29 | `Bwd IAT Max` | iat | мкс | Максимальний інтервал зворотного напрямку | Bwd IAT Max |
| 30 | `Bwd IAT Min` | iat | мкс | Мінімальний інтервал зворотного напрямку | Bwd IAT Min |
| 31 | `Fwd PSH Flags` | flags | кількість | Кількість прапорців PSH у прямому напрямку | Fwd PSH Flags |
| 32 | `Fwd Header Length` | header | байти | Сумарний розмір заголовків прямого напрямку | Fwd Header Length |
| 33 | `Bwd Header Length` | header | байти | Сумарний розмір заголовків зворотного напрямку | Bwd Header Length |
| 34 | `Fwd Packets/s` | rate | пакет/с | Інтенсивність пакетів прямого напрямку | Fwd Packets/s |
| 35 | `Bwd Packets/s` | rate | пакет/с | Інтенсивність пакетів зворотного напрямку | Bwd Packets/s |
| 36 | `Min Packet Length` | packet_length | байти | Мінімальний розмір пакета потоку | Min Packet Length |
| 37 | `Max Packet Length` | packet_length | байти | Максимальний розмір пакета потоку | Max Packet Length |
| 38 | `Packet Length Mean` | packet_length | байти | Середній розмір пакета потоку | Packet Length Mean |
| 39 | `Packet Length Std` | packet_length | байти | Стандартне відхилення розміру пакета потоку | Packet Length Std |
| 40 | `Packet Length Variance` | packet_length | байти² | Дисперсія розміру пакета потоку | Packet Length Variance |
| 41 | `FIN Flag Count` | flags | кількість | Кількість пакетів із прапорцем FIN | FIN Flag Count |
| 42 | `SYN Flag Count` | flags | кількість | Кількість пакетів із прапорцем SYN | SYN Flag Count |
| 43 | `RST Flag Count` | flags | кількість | Кількість пакетів із прапорцем RST | RST Flag Count |
| 44 | `PSH Flag Count` | flags | кількість | Кількість пакетів із прапорцем PSH | PSH Flag Count |
| 45 | `ACK Flag Count` | flags | кількість | Кількість пакетів із прапорцем ACK | ACK Flag Count |
| 46 | `URG Flag Count` | flags | кількість | Кількість пакетів із прапорцем URG | URG Flag Count |
| 47 | `ECE Flag Count` | flags | кількість | Кількість пакетів із прапорцем ECE | ECE Flag Count |
| 48 | `Down/Up Ratio` | rate | відношення | Відношення кількості пакетів зворотного напрямку до прямого (за пакетами, не за байтами) | Down/Up Ratio |
| 49 | `Average Packet Size` | packet_length | байти | Середній розмір пакета | Average Packet Size |
| 50 | `Avg Fwd Segment Size` | packet_length | байти | Середній розмір сегмента прямого напрямку | Avg Fwd Segment Size |
| 51 | `Avg Bwd Segment Size` | packet_length | байти | Середній розмір сегмента зворотного напрямку | Avg Bwd Segment Size |
| 52 | `Subflow Fwd Packets` | subflow | пакети | Середня кількість пакетів підпотоку прямого напрямку | Subflow Fwd Packets |
| 53 | `Subflow Fwd Bytes` | subflow | байти | Середня кількість байтів підпотоку прямого напрямку | Subflow Fwd Bytes |
| 54 | `Subflow Bwd Packets` | subflow | пакети | Середня кількість пакетів підпотоку зворотного напрямку | Subflow Bwd Packets |
| 55 | `Subflow Bwd Bytes` | subflow | байти | Середня кількість байтів підпотоку зворотного напрямку | Subflow Bwd Bytes |
| 56 | `Init_Win_bytes_forward` | tcp_window | байти | Початкове вікно TCP прямого напрямку; -1 означає, що значення відсутнє | Init_Win_bytes_forward |
| 57 | `Init_Win_bytes_backward` | tcp_window | байти | Початкове вікно TCP зворотного напрямку; -1 означає, що значення відсутнє | Init_Win_bytes_backward |
| 58 | `act_data_pkt_fwd` | tcp_window | пакети | Кількість пакетів прямого напрямку з ненульовим TCP-корисним навантаженням | act_data_pkt_fwd |
| 59 | `min_seg_size_forward` | tcp_window | байти | Мінімальний розмір сегмента прямого напрямку | min_seg_size_forward |
| 60 | `Active Mean` | active_idle | мкс | Середній час активності потоку | Active Mean |
| 61 | `Active Std` | active_idle | мкс | Стандартне відхилення часу активності | Active Std |
| 62 | `Active Max` | active_idle | мкс | Максимальний час активності | Active Max |
| 63 | `Active Min` | active_idle | мкс | Мінімальний час активності | Active Min |
| 64 | `Idle Mean` | active_idle | мкс | Середній час простою потоку | Idle Mean |
| 65 | `Idle Std` | active_idle | мкс | Стандартне відхилення часу простою | Idle Std |
| 66 | `Idle Max` | active_idle | мкс | Максимальний час простою | Idle Max |
| 67 | `Idle Min` | active_idle | мкс | Мінімальний час простою | Idle Min |

## Вилучені автоматично (сталі на train)

| Колонка | Опис |
| --- | --- |
| `Bwd PSH Flags` | Кількість прапорців PSH у зворотному напрямку |
| `Fwd URG Flags` | Кількість прапорців URG у прямому напрямку |
| `Bwd URG Flags` | Кількість прапорців URG у зворотному напрямку |
| `CWE Flag Count` | Кількість пакетів із прапорцем CWR |
| `Fwd Avg Bytes/Bulk` | Середня кількість байтів у пакетному блоці прямого напрямку |
| `Fwd Avg Packets/Bulk` | Середня кількість пакетів у блоці прямого напрямку |
| `Fwd Avg Bulk Rate` | Середня швидкість блоку прямого напрямку |
| `Bwd Avg Bytes/Bulk` | Середня кількість байтів у блоці зворотного напрямку |
| `Bwd Avg Packets/Bulk` | Середня кількість пакетів у блоці зворотного напрямку |
| `Bwd Avg Bulk Rate` | Середня швидкість блоку зворотного напрямку |

## Не використовуються як ознаки

| Колонка | Причина виключення |
| --- | --- |
| `Flow ID` | Ідентифікатор потоку, похідний від IP та портів; не є поведінковою ознакою |
| `Source IP` | Ідентифікатор конкретного вузла стенду; ризик запам'ятовування адрес атакувальників |
| `Destination IP` | Ідентифікатор конкретного вузла стенду; ризик запам'ятовування адрес жертв |
| `Source Port` | Ефемерний номер порту; числова величина не має порядкового змісту |
| `Destination Port` | Категоріальний номер сервісу; числова величина не має порядкового змісту, ризик прив'язки до портів стенду |
| `Timestamp` | Використовується для часу події, але не як ознака: час доби пов'язаний із розкладом атак у стенді |
| `Fwd Header Length.1` | Точна копія Fwd Header Length (перевіряється під час завантаження) |
| `Label` | Цільова мітка; використовується лише для поділу, вибору порога й оцінювання |

## Перевірка таблиці 2.2 чернетки звіту практики

Чернетка змішує потокові ознаки з HTTP-метриками сервера. Частини ознак у CICIDS2017 немає, тому переносити таблицю не можна.

| Ознака чернетки | Доступна | Відповідник у CICIDS2017 | Коментар |
| --- | --- | --- | --- |
| `request_rate` | Немає | Flow Packets/s (лише наближено) | У CICIDS2017 немає поняття запиту; є інтенсивність пакетів окремого потоку |
| `connection_count` | Немає | — | Набір містить по одному запису на потік; кількість з'єднань за вікно не реалізована |
| `src_bytes` | Частково | Total Length of Fwd Packets | Напрям визначено першим пакетом потоку, а не роллю сервера |
| `dst_bytes` | Частково | Total Length of Bwd Packets | Напрям визначено першим пакетом потоку, а не роллю сервера |
| `error_rate` | Немає | — | HTTP-коди відповідей у наборі відсутні |
| `avg_response_time` | Немає | — | Час відповіді прикладного рівня відсутній; Flow IAT є інтервалом між пакетами, а не часом відповіді |
| `unique_src_ips` | Немає | — | Source IP є, але агрегація за часовими вікнами не реалізована, а IP виключено з ознак |
| `protocol_type` | Так | Protocol → protocol_tcp, protocol_udp | Номер IP-протоколу, закодований бінарно |
| `status_code_group` | Немає | — | HTTP-коди відповідей у наборі відсутні |
| `traffic_ratio` | Частково | Down/Up Ratio | Відношення за кількістю пакетів, а не за обсягом |
