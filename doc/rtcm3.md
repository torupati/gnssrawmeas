RTCM3.2 Observation Message Table
=================================

This is a list of the main RTCM3.2 observation message types and their contents. MSM (Multiple Signal Messages) can be extended flexibly depending on the observable signal types and station/satellite combinations.

| Message number | Name/format | Contents/usage | Notes |
| --- | --- | --- | --- |
| 1001 | GPS L1-only | L1 pseudorange | Basic observation (low precision) |
| 1002 | GPS L1-only | L1 pseudorange + carrier phase | Basic observation (medium precision) |
| 1003 | GPS L1-only | L1 pseudorange + carrier phase + Doppler | Basic observation |
| 1004 | GPS L1-only | L1 pseudorange + carrier phase + Doppler + C/N0 | Basic observation |
| 1009 | GLONASS L1-only | L1 pseudorange | Basic observation (low precision) |
| 1010 | GLONASS L1-only | L1 pseudorange + carrier phase | Basic observation (medium precision) |
| 1011 | GLONASS L1-only | L1 pseudorange + carrier phase + Doppler | Basic observation |
| 1012 | GLONASS L1-only | L1 pseudorange + carrier phase + Doppler + C/N0 | Basic observation |
| 1071 | GPS MSM1 | MSM ranges + coarse phase | MSM (low precision) |
| 1072 | GPS MSM2 | MSM ranges + phase + Doppler | MSM |
| 1073 | GPS MSM3 | MSM ranges + phase + C/N0 | MSM |
| 1074 | GPS MSM4 | MSM ranges + phase + Doppler + C/N0 | MSM |
| 1075 | GPS MSM5 | MSM high-precision ranges + phase + Doppler + C/N0 | MSM (high precision) |
| 1076 | GPS MSM6 | MSM high-precision ranges + phase + Doppler + C/N0 + range rate | MSM (high precision) |
| 1077 | GPS MSM7 | MSM highest precision (full) | MSM (highest precision) |
| 1081 | GLONASS MSM1 | MSM ranges + coarse phase | MSM (low precision) |
| 1082 | GLONASS MSM2 | MSM ranges + phase + Doppler | MSM |
| 1083 | GLONASS MSM3 | MSM ranges + phase + C/N0 | MSM |
| 1084 | GLONASS MSM4 | MSM ranges + phase + Doppler + C/N0 | MSM |
| 1085 | GLONASS MSM5 | MSM high-precision ranges + phase + Doppler + C/N0 | MSM (high precision) |
| 1086 | GLONASS MSM6 | MSM high-precision ranges + phase + Doppler + C/N0 + range rate | MSM (high precision) |
| 1087 | GLONASS MSM7 | MSM highest precision (full) | MSM (highest precision) |
| 1091 | Galileo MSM1 | MSM ranges + coarse phase | MSM (low precision) |
| 1092 | Galileo MSM2 | MSM ranges + phase + Doppler | MSM |
| 1093 | Galileo MSM3 | MSM ranges + phase + C/N0 | MSM |
| 1094 | Galileo MSM4 | MSM ranges + phase + Doppler + C/N0 | MSM |
| 1095 | Galileo MSM5 | MSM high-precision ranges + phase + Doppler + C/N0 | MSM (high precision) |
| 1096 | Galileo MSM6 | MSM high-precision ranges + phase + Doppler + C/N0 + range rate | MSM (high precision) |
| 1097 | Galileo MSM7 | MSM highest precision (full) | MSM (highest precision) |
| 1101 | SBAS MSM1 | MSM ranges + coarse phase | MSM (low precision) |
| 1102 | SBAS MSM2 | MSM ranges + phase + Doppler | MSM |
| 1103 | SBAS MSM3 | MSM ranges + phase + C/N0 | MSM |
| 1104 | SBAS MSM4 | MSM ranges + phase + Doppler + C/N0 | MSM |
| 1105 | SBAS MSM5 | MSM high-precision ranges + phase + Doppler + C/N0 | MSM (high precision) |
| 1106 | SBAS MSM6 | MSM high-precision ranges + phase + Doppler + C/N0 + range rate | MSM (high precision) |
| 1107 | SBAS MSM7 | MSM highest precision (full) | MSM (highest precision) |
| 1111 | QZSS MSM1 | MSM ranges + coarse phase | MSM (low precision) |
| 1112 | QZSS MSM2 | MSM ranges + phase + Doppler | MSM |
| 1113 | QZSS MSM3 | MSM ranges + phase + C/N0 | MSM |
| 1114 | QZSS MSM4 | MSM ranges + phase + Doppler + C/N0 | MSM |
| 1115 | QZSS MSM5 | MSM high-precision ranges + phase + Doppler + C/N0 | MSM (high precision) |
| 1116 | QZSS MSM6 | MSM high-precision ranges + phase + Doppler + C/N0 + range rate | MSM (high precision) |
| 1117 | QZSS MSM7 | MSM highest precision (full) | MSM (highest precision) |
| 1121 | BeiDou MSM1 | MSM ranges + coarse phase | MSM (low precision) |
| 1122 | BeiDou MSM2 | MSM ranges + phase + Doppler | MSM |
| 1123 | BeiDou MSM3 | MSM ranges + phase + C/N0 | MSM |
| 1124 | BeiDou MSM4 | MSM ranges + phase + Doppler + C/N0 | MSM |
| 1125 | BeiDou MSM5 | MSM high-precision ranges + phase + Doppler + C/N0 | MSM (high precision) |
| 1126 | BeiDou MSM6 | MSM high-precision ranges + phase + Doppler + C/N0 + range rate | MSM (high precision) |
| 1127 | BeiDou MSM7 | MSM highest precision (full) | MSM (highest precision) |
| 1131 | NavIC/IRNSS MSM1 | MSM ranges + coarse phase | MSM (low precision) |
| 1132 | NavIC/IRNSS MSM2 | MSM ranges + phase + Doppler | MSM |
| 1133 | NavIC/IRNSS MSM3 | MSM ranges + phase + C/N0 | MSM |
| 1134 | NavIC/IRNSS MSM4 | MSM ranges + phase + Doppler + C/N0 | MSM |
| 1135 | NavIC/IRNSS MSM5 | MSM high-precision ranges + phase + Doppler + C/N0 | MSM (high precision) |
| 1136 | NavIC/IRNSS MSM6 | MSM high-precision ranges + phase + Doppler + C/N0 + range rate | MSM (high precision) |
| 1137 | NavIC/IRNSS MSM7 | MSM highest precision (full) | MSM (highest precision) |
| 1230 | GLONASS code/phase bias | FDMA code and phase bias correction | Observation support |

Note: 1001-1012 are legacy formats, and 1071-1137 are MSM formats. MSM supports multiple frequencies and signal codes.
