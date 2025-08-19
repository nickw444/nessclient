# D8-16X Serial Interface Protocol

**Revision:** 16  
**Date of issue:** 22-11-04  
**Document ID:** 3627S27.doc

This Document is copyright. No part maybe reproduced by any process without written permission

---

## Disclaimer

Ness Corporation may change the information in this document without notice. A print version is always uncontrolled.

Ness Corporation bears no responsibility or liability for third party useage of this document in product designs not involving Ness Corporation.

No technical assistance will be provided for implementation of interfaces and/or products that utilise this specification.

**UNCONTROLLED COPY IF PRINTED**  
**Doc ID. D8-32X SERIAL PROTOCOL.DOC**

---

## INTRODUCTION

The D32X ALARM PANELS RS232 serial interface allows communication between various external devices. This document details the input and outputs messages – all of which use an ASCII Protocol.

**The ASCII outputs are:**
1. Event data.
2. Panel status.

**The ASCII inputs are:**
- Keypad strings
- User code entry  
- Arming

**The serial data is always 9600 baud, 8 data bits, no parity, 1 stop bit.**

**NOTE:** This document refers to hexadecimal numbers, which are represented by the prefix 0x. Decimal numbers have no prefix.

## 1. Output Event Data

These messages are sent as they occur in the D32x. The format of the message is:

| NAME | START | ADDRESS | LENGTH | COMMAND | DATA | TIME STAMP (decimal bytes) | CHECKSUM | FINISH |
|------|-------|---------|--------|---------|------|---------------------------|----------|---------|
| LENGTH | 1 BYTE | 1 BYTE | 1 BYTE | 1 BYTE | 3 BYTES | 6 BYTES | 1 BYTE | 2 BYTES |
| ID | ST | AD | L | CM | E I D | A R Y M D D H M SC | CK | CR LF |
| TYPE | HEX | HEX | HEX | HEX | HEX DEC HEX | DEC DEC DEC DEC DEC DEC | HEX | HEX HEX |

### 1. START.

The START byte defines the structure of the message being sent.

Output Event Data on the D32X is always an ASCII message with optional Address & Time Stamp. Therefore the START byte for the Output Event Data on the D32X is derived from the following bit definitions.

| BIT | Parameter | Definition | Program Option |
|-----|-----------|------------|----------------|
| 1 (0x01) | ADDRESS included | P199E 1E |
| 2 (0x02) | Basic header - always SET | NONE - Fixed ON |
| 3 (0x04) | TIME STAMP included | P199E 2E |
| 4-6 | Not used | NONE - Always OFF |
| 7 (0x80) | ASCII format | NONE - Fixed ON |

**NOTE:** Values starting with 0x (such as 0x80) signify a hexadecimal number.

This table shows the START value for different address/ time stamp selections.

| START BYTE (hex) | ADDRESS included | DATE/TIME included | P199E 1E | P199E 2E |
|------------------|------------------|-------------------|----------|----------|
| 87 | Y | Y | On | On |
| 86 | N | Y | Off | On |
| 83 | Y | N | On | Off |
| 82 | N | N | Off | Off |

### 2. ADDRESS.

The ADDRESS byte identifies the D32X sending the message.

The address is either 0x00 or the last digit of the Account Number 2 (P73E).

Range is 0x00 to 0x0F (the Account Number can include hex numbers).

**EXAMPLE:** If Account Number 2 = 1234, ADDRESS = 4.

### 3. TIME STAMP.

These values are in decimal format.

The time stamp includes the DATE and TIME.

It is 6 bytes – YEAR, MONTH, DAY of Week & DAY of Month, HOURS, MINUTES & SECONDS.

1. **YEAR** - 00 to 99.
2. **MONTH** - 01 (January) to 12 (December).
3. **DAY of MONTH** - 1 to 31. The 3 MSB can also be used to represent the Day of the week, with 1 = MONDAY.
4. **HOURS** – 00 (midnight) to 23 (11pm) (12 is midday). Always 24hr format. The 3 MSB can also be used to represent Daylight Saving.
5. **MINUTES** – 0 to 59.
6. **SECONDS** – 0 to 59

### 4. LENGTH & SEQUENCE NUMBER BIT.

The SEQUENCE NUMBER BIT is the MSB of the LENGTH byte. It is either 0 or 1.

For each new message the sequence number bit is toggled.

The length of the Output Event Data is always 3 bytes.

Therefore this byte is either 0x03 or 0x83 – depending on the sequence bit.

### 5. COMMAND.

This byte is fixed at 0x61 to indicate a SYSTEM STATUS message.

### 6. DATA MESSAGE.

The data message is always 3 bytes to identify the EVENT, the ID and the AREA data.

#### a. EVENT. The EVENT categories are:

**Zone or User EVENTS**

| Value | Description | Applicable ID |  | Applicable AREA |  | Comment |
|-------|-------------|---------------|---|-----------------|---|---------|
|  |  | Value | Description | Value | Description |  |
| 0x01 | Sealed | 00 | Power up | 0x00 | No Area | Power up or reset |
|  |  | 0x00 0x01 | Unsealed Sealed | 01 to 32 | Zone 1 to 32 | 0x00 | No Area | Current zone state |
|  |  | 01 to 56 | User 1 to 56 | 0xa1 to 0xa3 | Door 1 to Door 3 | User access door |
| 0x02 0x03 | Alarm Alarm Restore | 01 to 32 | Zone 1 to 32 | 0x01 0x02 0x03 0x04 0x80 0x81 0x85 | Area 1 Area 2 Home Day 24 hr Fire Door | When Armed Area 1 When Armed Area 2 When Armed Home When Armed Day 24 hr 24hr converted to Fire Door Open too Long |
|  |  | 0xf0 | Keypad | 0x81 0x82 0x83 0x84 | Fire Panic Medical Duress | Keypad Fire Keypad Panic Keypad Medical Keypad Duress |
|  |  | 01 to 56 | User 1 to 56 | 0x82 | Panic | Radio Panic |
|  |  | 0x00 | Main Unit | 0x82 | Panic | Keyswitch Panic |
| 0x04 0x05 | Manual Exclude Manual Include | 01 to 32 | Zone 1 to 32 | 0x00 | Area 1 Area 2 Home 24 hr | When Armed Area 1 When Armed Area 2 When Armed Home 24 hr |

| 0x06 0x07 | Auto Exclude Auto Include | 01 to 32 | Zone 1 to 32 | 0x00 | Area 1 Area 2 Home 24 hr | When Armed Area 1 When Armed Area 2 When Armed Home 24 hr |
| 0x08 0x09 | Tamper Unsealed Tamper Normal | 0x00 | Main Unit | 0x00 0x01 | Internal External | Internal Tamper External Tamper |
|  |  | 0xF0 | Keypad | 0x00 | No Area | Keypad Tamper |
|  |  | 01 to 32 | Zone 1 to 32 | 0x91 | Radio Detector | Radio Detector Tamper |

**System EVENTS**

| Value | Description | Applicable ID |  | Applicable AREA |  | Comment |
|-------|-------------|---------------|---|-----------------|---|---------|
|  |  | Value | Description | Value | Description |  |
| 0x10 0x11 | Power Failure Power Normal | 0x00 | Main Unit | 0x00 | No Area | AC Mains Fail AC Mains Restored |
| 0x12 0x13 | Battery Failure Battery Normal | 0x00 | Main Unit | 0x00 | No Area | Main Battery |
|  |  | 01 to 56 | User 1 to 56 | 0x92 | Radio Key | Radio Key Battery |
|  |  | 01 to 32 | Zone 1 to 32 | 0x91 | Radio Detector | Radio Detector Battery |
| 0x14 0x15 | Report Failure Report Normal | 0x00 | Main Unit | 0x00 | No Area | Dialler Fail to report |
| 0x32 0x17 | Supervision Failure Supervision Normal | 01 to 32 | Zone 1 to 32 | 0x00 | No Area | Supervised zone failure |
| 0x19 | Real Time Clock | 0x00 | Main Unit | 0x00 | No Area | RTC Time or Date Changed |

**Area EVENTS**

| Value | Description | Applicable ID |  | Applicable AREA |  | Comment |
|-------|-------------|---------------|---|-----------------|---|---------|
|  |  | Value | Description | Value | Description |  |
| 0x20 0x21 | Entry Delay Start Entry Delay End | 01 to 32 | Zone 1 to 32 | 0x01 0x02 0x03 | Area 1 Area 2 Home | When Armed Area 1 When Armed Area 2 When Armed Home |
| 0x22 0x23 | Exit Delay Start Exit Delay End | 01 to 32 | Zone 1 to 32 | 0x01 0x02 0x03 | Area 1 Area 2 Home | When Armed Area 1 When Armed Area 2 When Armed Home |
| 0x24 | Armed Away | 01 to 56 57 58 | User 1 to 56 Keyswitch 57 Short Arm 58 | 0x01 0x02 | Area 1 Area 2 | When Armed Area 1 When Armed Area 2 |
| 0x25 | Armed Home | 01 to 56 57 58 | User 1 to 56 Keyswitch 57 Short Arm 58 | 0x03 | Home | When Armed Home |
| 0x26 | Armed Day |  |  | 0x04 | Day | When Armed Day |
| 0x27 | Armed Night | - | - | - | - |  |
| 0x28 | Armed Vacation | - | - | - | - |  |
| 0x2e | Armed Highest | - | - | - | - |  |
| 0x2f | Disarmed | 01 to 56 57 58 | User 1 to 56 Keyswitch 57 | 0x01 0x02 0x03 0x04 | Area 1 Area 2 Home Day |  |
| 0x30 | Arming delayed | 01 to 56 | User 1 to 56 | 0x01 0x02 0x03 | Area 1 Area 2 Home | Auto arming delayed |

**Result EVENTS**

| Value | Description | Applicable ID |  | Applicable AREA |  | Comment |
|-------|-------------|---------------|---|-----------------|---|---------|
|  |  | Value | Description | Value | Description |  |
| 0x31 0x32 | Output On Output Off | 01 to 10 090 091 092 093 094 095 096 097 | Aux 1 to 10 Siren Soft Siren Soft Home Siren Fire Strobe Reset Sonalert Keypad Display Enable | 0x00 | - | Outputs on D8x/D32x |

### 7. CHK. 

The checksum byte HEX character results in the LSB being zero when all the message bytes are summed. *This is done before the message is converted to ASCII and excludes the FINISH bytes.*

### 8. FINISH. 

This is always CR, LF (Carriage Return, Line Feed).

---

## 2. INPUT COMMANDS

There are 2 types of input commands:
1. Keypad strings.
2. Status Requests.

The format of the input message is:

| NAME | START | ADDRESS | LENGTH | COMMAND | DATA | CHECKSUM | FINISH |
|------|-------|---------|--------|---------|------|----------|---------|
| LENGTH | 1 BYTE | 1 BYTE | 1 BYTE | 1 BYTE | 1 – 30 BYTES | 1 BYTE | 0-3 BYTES |
| ID | ST | AD | L | CM |  | CK | CR LF |
| TYPE | HEX | HEX | HEX | HEX |  | HEX |  |

**Example:** 83 0 05 60 A123E ? CR LF  
38 33 30 30 35 36 30 41 31 32 33 45 31 32 3F 0D 0A

### 1. START.

The START byte defines the structure of the message being sent.

Input Event Data on the D32X is an ASCII message.

This table shows the START value:

| START BYTE (hex) | ADDRESS included | DATE/TIME included |
|------------------|------------------|-------------------|
| 83 | Y | N |

### 2. ADDRESS.

The ADDRESS byte identifies the D32X receiving the message.

The address is either 0x0 or the last digit of the Account Number 2 (P73E).

Range is 0x00 to 0x0F (the Account Number can include hex numbers).

**EXAMPLE:** If Account Number 2 = 1234, ADDRESS = 4.
i) An address of 0 is always accepted.
ii) An address other than 0 must match the last digit of P73E.

### 3. LENGTH. 
The length of the Input Event Data is variable with a maximum of 30 bytes.

### 4. COMMAND. 
This byte is fixed at 0x60 to indicate a CMD USER INTERFACE message.

### 5. DATA. 
The DATA is from 1 to 30 bytes.

| Ascii | Name | Description |
|-------|------|-------------|
| A | Arm Key | ARM key |
| H | Home Key | HOME or MONITOR key |
| E | Enter Key | ENTER or E key |
| X | Exclude Key | EXCLUDE key |
| F | Fire Key | FIRE key |
| V | View Key | MEMORY key |
| P | Panic Key | PANIC key (same as pressing double panic) |
| D | Medical Key | MEDICAL key |
| M | Program Key | PROGRAM or P key |
| * | Panic1 Key | * Key (* on LHS of keypad) |
| # | Panic2 Key | # Key (* on RHS of keypad) |
| 0-9 | 0-9 Keys | Number keys |
| S | Status update | STATUS request (not a key). Followed by a 2 digit ID. |

### 6. CHK. 
The checksum is calculated after the message is converted to ASCII.
a. All the ASCII characters up to the checksum position are added together.
b. The least significant byte (LSB) of the addition is then used to calculate the checksum CHK.
c. LSB + CHK = 100 hex.
d. CHK is then converted into 2 ASCII characters and added to the message.

**Examples: Status request for unsealed zones.**

| NAME | START | ADD | LEN | CMD | DATA | CHK | Delay | FINISH |
|------|-------|-----|-----|-----|------|-----|-------|---------|
| Status 0 | 83 | 00 | 03 | 60 | S 0 0 | E9 | ? | CR LF |
|  | 38 33 | 30 30 | 33 | 36 30 | 53 30 30 | 45 39 | 3F | 0D 0A |

1. 38+33+30+30+33+36+30+53+30+30 = 217. (LSB = 17)
2. 17+E9 = 100. (CHK = E9)

**Arm using code 123**

| NAME | START | ADD | LEN | CMD | DATA | CHK | Delay | FINISH |
|------|-------|-----|-----|-----|------|-----|-------|---------|
| ARM123E | 83 | 00 | 05 | 60 | A 1 2 3 E | 7E | ? | CR LF |
|  | 38 33 | 30 30 | 35 | 36 30 | 41 31 32 33 45 | 37 45 | 3F | 0D 0A |

1. 38+33+30+30+35+36+30+41+31+32+33+45 = 282. (LSB = 82)
2. 82+7E = 100. (CHK = 7E)

### 7. FINISH. 
It includes:
a. **?** - Command Separator. If a number of messages are sent together then they should be separated by '?'. This adds a delay between processing successive messages.
b. **CR** - Carriage Return. Optional - it is ignored by the panel.
c. **LF** - Line Feed. Optional - it is ignored by the panel

---

## Status update

This is sent in response to a STATUS request.

STATUS allows remote viewing of the current arming and alarm states.

The format of the status message is:

| NAME | START | ADDRESS | LENGTH | COMMAND | DATA | CHKSUM | FINISH |
|------|-------|---------|--------|---------|------|--------|---------|
| LENGTH | 1 BYTE | 1 BYTE | 1 BYTE | 1 BYTE | 3 BYTES | 1 BYTE | 2 BYTES |
| ID | ST | AD | L | CM |  | CK | CR LF |
| TYPE | HEX | HEX | HEX | HEX |  | HEX |  |
| Example | 82 | 07 | 03 | 60 | 00 40 00 | 13 | CR LF |
|  | 38 32 | 30 37 | 30 33 | 36 30 | 30 30 34 30 30 30 | 31 33 | 0D 0A |

*(This message reports a zone 7 unseal on D8x panel with address 7)*

### 8. START.
The START byte defines the structure of the message being sent.
Status report Data on the D32X is an ASCII message = 82 .

### 9. ADDRESS.
The ADDRESS byte identifies the D32X receiving the message.
The address is either 0x00 or the last digit of the Account Number 2 (P73E).
Range is 0x00 to 0x0F (the Account Number can include hex numbers).
**EXAMPLE:** If Account Number 2 = 1234, ADDRESS = 4.
iii) An address of 0 is always accepted.
iv) An address other than 0 must match the last digit of P73E.

### 10. LENGTH.
The length of the Status Data is fixed at 3 bytes.

### 11. COMMAND.
This byte is fixed at 0x60 to indicate a **CMD USER INTERFACE** message.

### 12. DATA.
The DATA is 3 bytes.
The 1st byte is the received status request ID.
The 2nd & 3rd bytes are the data as explained below.

| ID No | Description | Size (bytes) | Rules |
|-------|-------------|--------------|-------|
| 0 | Zone 1-16 Input Unsealed | 2 | FORM 4. Zones 1-16 |
| 1 | Zone 1-16 Radio Unsealed | 2 | FORM 4. Zones 1-16 |
| 2 | Zone 1-16 CBus Unsealed | 2 | FORM 4. Zones 1-16 |
| 3 | Zone 1-16 in Delay | 2 | FORM 4. Zones 1-16 |
| 4 | Zone 1-16 in Double Trigger | 2 | FORM 4. Zones 1-16 |
| 5 | Zone 1-16 in Alarm | 2 | FORM 4. Zones 1-16 |
| 6 | Zone 1-16 Excluded | 2 | FORM 4. Zones 1-16 |
| 7 | Zone 1-16 Auto Excluded | 2 | FORM 4. Zones 1-16 |
| 8 | Zone 1-16 Supervision Fail Pending | 2 | FORM 4. Zones 1-16 |
| 9 | Zone 1-16 Supervision Fail | 2 | FORM 4. Zones 1-16 |
| 10 | Zone 1-16 Doors Open | 2 | FORM 4. Zones 1-16 |
| 11 | Zone 1-16 Detector Low Battery | 2 | FORM 4. Zones 1-16 |
| 12 | Zone 1-16 Detector Tamper | 2 | FORM 4. Zones 1-16 |
| 13 | Miscellaneous Alarms | 2 | FORM 20. Miscellaneous alarms. |
| 14 | Arming | 2 | FORM 21. |
| 15 | Outputs | 2 | FORM 22. |
| 16 | View State | 2 | FORM 23. |
| 17 | VERSION - SW | 2 | mmxy<br>mm – model<br>D16X - 00h<br>D16X 3G - 04h<br>D16X 4G - 05h<br>D32X - 06h<br>xy - sw version<br>x 0-f (4 bits msb)<br>y 0-f (4 bits lsb)<br>See VERSION examples BELOW |
| 18 | AUXILIARY OUTPUTS | 2 | FORM 24. |
| 19 | Zone 1-16 Excluded + Auto Excluded | 2 | FORM 4. Zones 1-16 |
| 20 | Zone 17-32 Input Unsealed | 2 | FORM 5. Zones 17-32 |
| 21 | Zone 17-32 Radio Unsealed | 2 | FORM 5. Zones 17-32 |
| 22 | Zone 17-32 CBus Unsealed | 2 | FORM 5. Zones 17-32 |
| 23 | Zone 17-32 in Delay | 2 | FORM 5. Zones 17-32 |
| 24 | Zone 17-32 in Double Trigger | 2 | FORM 5. Zones 17-32 |
| 25 | Zone 17-32 in Alarm | 2 | FORM 5. Zones 17-32 |
| 26 | Zone 17-32 Excluded | 2 | FORM 5. Zones 17-32 |
| 27 | Zone 17-32 Auto Excluded | 2 | FORM 5. Zones 17-32 |
| 28 | Zone 17-32 Supervision Fail Pending | 2 | FORM 5. Zones 17-32 |
| 29 | Zone 17-32 Supervision Fail | 2 | FORM 5. Zones 17-32 |
| 30 | Zone 17-32 Doors Open | 2 | FORM 5. Zones 17-32 |
| 31 | Zone 17-32 Detector Low Battery | 2 | FORM 5. Zones 17-32 |
| 32 | Zone 17-32 Detector Tamper | 2 | FORM 5. Zones 17-32 |
| 33 | Zone 17-32 Excluded + Auto Excluded | 2 | FORM 5. Zones 17-32 |

## FORM 4. Used to select Zones 1-16.

| Name | DATA | EXAMPLE | COMMENT |
|------|------|---------|---------|
| Zone 1 | 0100 | 82 07 03 60 05 01 00 0e CR LF | 05 = Alarm, 0100 = zone 1 (panel address = 07) |
| Zone 2 | 0200 |  |  |
| Zone 3 | 0400 |  |  |
| Zone 4 | 0800 |  |  |
| Zone 5 | 1000 |  |  |
| Zone 6 | 2000 |  |  |
| Zone 7 | 4000 | 82 07 03 60 00 40 00 13 CR LF | 00 = unseal, 4000 = zone 7 (panel address = 07) |
| Zone 8 | 8000 | 82 07 03 60 00 c0 00 54 CR LF | 00 = unseal, c000 = zone 7 & zone 8 (panel address = 07) |
| Zone 9 | 0001 |  |  |
| Zone 10 | 0002 |  |  |
| Zone 11 | 0004 |  |  |
| Zone 12 | 0008 |  |  |
| Zone 13 | 0010 |  |  |
| Zone 14 | 0020 |  |  |
| Zone 15 | 0040 |  |  |
| Zone 16 | 0080 | 82 07 03 60 00 00 80 94 | 00 = unseal, 0080 = zone 16 (panel address = 07) |

## FORM 5. Used to select Zones 17-32.

| Name | DATA | EXAMPLE | COMMENT |
|------|------|---------|---------|
| Zone 17 | 0100 | 82 07 03 60 25 01 00 0e CR LF | 05 = Alarm, 0100 = zone 17 (panel address = 07) |
| Zone 18 | 0200 |  |  |
| Zone 19 | 0400 |  |  |
| Zone 20 | 0800 |  |  |
| Zone 21 | 1000 |  |  |
| Zone 22 | 2000 |  |  |
| Zone 23 | 4000 | 82 07 03 60 20 40 00 13 CR LF | 00 = unseal, 4000 = zone 23 (panel address = 07) |
| Zone 24 | 8000 | 82 07 03 60 20 c0 00 54 CR LF | 00 = unseal, c000 = zone 23 & zone 24 (panel address = 07) |
| Zone 25 | 0001 |  |  |
| Zone 26 | 0002 |  |  |
| Zone 27 | 0004 |  |  |
| Zone 28 | 0008 |  |  |
| Zone 29 | 0010 |  |  |
| Zone 30 | 0020 |  |  |
| Zone 31 | 0040 |  |  |
| Zone 32 | 0080 | 82 07 03 60 20 00 80 94 | 00 = unseal, 0080 = zone 32 (panel address = 07) |

## FORM 20. Show Miscellaneous alarms.

| Name | DATA |
|------|------|
| Duress | 0001 |
| Panic | 0002 |
| Medical | 0004 |
| Fire | 0008 |
| Instal End | 0010 |
| Ext Tamper | 0020 |
| Panel Tamper | 0040 |
| Keypad Tamper | 0080 |
| Pendant Panic | 0100 |
| Panel Battery Low | 0200 |
| Panel Battery Low | 0400 |
| Mains Fail | 0800 |
| CBus Fail | 1000 |
|  | 2000 |
|  | 4000 |
|  | 8000 |

## FORM 21. Show ARMING STATUS.

| Name | DATA |
|------|------|
| AREA 1 ARMED | 0100 |
| AREA 2 ARMED | 0200 |
| AREA 1 FULLY ARMED | 0400 |
| AREA 2 FULLY ARMED | 0800 |
| HOME ARMED | 1000 |
| Day Mode Armed | 2000 |
| Entry Delay 1 ON | 4000 |
| Entry Delay 2 ON | 8000 |
| Manual Exclude mode | 0001 |
| Memory mode | 0002 |
| Day Zone Select | 0004 |
|  | 0008 |
|  | 0010 |
|  | 0020 |
|  | 0040 |
|  | 0080 |

## FORM 22. Show output states.

| Name | DATA |
|------|------|
| Siren Loud | 0100 |
| Siren Soft | 0200 |
| Siren Soft Home | 0400 |
| Siren Fire | 0800 |
| Strobe | 1000 |
| Reset | 2000 |
| Sonalert | 4000 |
| Keypad Display Enable | 8000 |
| Aux1 | 0001 |
| Aux2 | 0002 |
| Aux3 | 0004 |
| Aux4 | 0008 |
| Home Out | 0010 |
| Power Fail | 0020 |
| Panel Batt Fail | 0040 |
| Tamper Xpand | 0080 |

## FORM 23. Show View states.

| Name | DATA |
|------|------|
| NORMAL | F000 |
| BRIEF DAY (CHIME) | E000 |
| HOME | D000 |
| MEMORY | C000 |
| BRIEF DAY ZONE SELECT | B000 |
| EXCLUDE SELECT | A000 |
| USER PROGRAM | 9000 |
| INSTALLER PROGRAM | 8000 |

## FORM 24. Show Auxiliary output states.

| Name | DATA |
|------|------|
| Aux1 | 0001 |
| Aux2 | 0002 |
| Aux3 | 0004 |
| Aux4 | 0008 |
| Aux5 | 0010 |
| Aux6 | 0020 |
| Aux7 | 0040 |
| Aux8 | 0080 |

### 13. CHK. 
The checksum byte HEX character results in the LSB being zero when all the message bytes are summed. *This is done before the message is converted to ASCII and excludes the FINISH bytes.*

### 14. FINISH. 
It includes:
a. **CR** - Carriage Return. Optional - it is ignored by the panel.
b. **LF** - Line Feed. Optional - it is ignored by the panel

---

## Program Options

### P199E - ASCII Bus Options

1E. Include address in message. The address is the lower byte of P73E.  
2E. Include time stamp in output message.  
3E. Include Alarms in output message.  
4E. Include Warnings in output message.  
5E. Include Access Events in output message.  
6E. Zone Seal State (D8x/D32x V6 and later).  
7E. Send a periodic VERSION -SW message if P199E 7E is ON. Intended as an OK ID signal.

---

## EXAMPLES

The following tables list the messages sent with an example showing the string data and below it the actual ASCII byte output (ie 80 is sent as the ascii bytes 38 30).

### ALARM

#### Duress
- **Example:** D32 2 User1 07:43 1:2:2006

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 02 | 01 | 84 | 06 | 12 | 01 | 07 | 43 | 00 | 8D | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 32 | 30 31 | 38 34 | 30 36 | 31 32 | 30 31 | 30 37 | 34 33 | 30 30 | 38 44 | 0d 0a |

#### Fire
- **Example:** Zone 1 09:43 1:2:2006

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 02 | 04 | 81 | 06 | 02 | 01 | 09 | 43 | 00 | 9B | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 32 | 30 31 | 38 31 | 30 36 | 30 32 | 30 31 | 30 39 | 34 33 | 30 30 | 39 42 | 0d 0a |

#### Medical
- **Example:** User 1 13:15 2:3:2006

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 02 | 01 | 83 | 06 | 02 | 01 | 13 | 15 | 00 | C0 | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 32 | 30 31 | 38 33 | 30 36 | 30 32 | 30 31 | 31 33 | 31 35 | 30 30 | 43 30 | 0d 0a |

#### Panic Radio Key
- **Example:** User 50 13:15 2:3:2006

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 02 | 32=50d | 82 | 06 | 02 | 01 | 13 | 15 | 00 | 90 | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 32 | 33 32 | 38 32 | 30 36 | 30 32 | 30 31 | 31 33 | 31 35 | 30 30 | 39 30 | 0d 0a |

#### Panic Keypad
- **Example:** 13:15 2:3:2006

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 02 | 39=57d | 82 | 06 | 02 | 01 | 13 | 15 | 00 | 89 | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 32 | 33 39 | 38 32 | 30 36 | 30 32 | 30 31 | 31 33 | 31 35 | 30 30 | 38 39 | 0d 0a |

#### Panic Keyswitch
- **Example:** 13:15 2:3:2006

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 02 | 3A=58d | 82 | 06 | 02 | 01 | 13 | 15 | 00 | 88 | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 32 | 33 41 | 38 32 | 30 36 | 30 32 | 30 31 | 31 33 | 31 35 | 30 30 | 38 38 | 0d 0a |

#### Tamper Internal Panel
- **Example:** 23:45 10:5:2008

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 08 | 00 | 00 | 08 | 05 | 10 | 23 | 45 | 00 | EA | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 38 | 30 30 | 30 30 | 30 38 | 30 35 | 31 30 | 32 33 | 34 35 | 30 30 | 45 41 | 0d 0a |

#### Tamper Radio Detector
- **Example:** Zone 15 Area 1 23:45 10:5:2008

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 08 | 0F=15d | 91 | 08 | 05 | 10 | 23 | 45 | 00 | DA | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 38 | 30 46 | 30 31 | 30 38 | 30 35 | 31 30 | 32 33 | 34 35 | 30 30 | 44 41 | 0d 0a |

#### Tamper External
- **Example:** 23:45 10:5:2008

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 08 | 39=57d | 00 | 08 | 05 | 10 | 23 | 45 | 00 | B1 | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 38 | 30 39 | 30 30 | 30 38 | 30 35 | 31 30 | 32 33 | 34 35 | 30 30 |  | 0d 0a |

#### Tamper Keypad
- **Example:** 23:45 10:5:2008

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 08 | F0 | 00 | 08 | 05 | 10 | 23 | 45 | 00 | FA | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 38 | 46 30 | 30 30 | 30 38 | 30 35 | 31 30 | 32 33 | 34 35 | 30 30 |  | 0d 0a |

#### Zone
- **Example:** Zone 12 Area 1 23:45 10:5:2008

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 02 | 0c=12 | 01 | 08 | 05 | 10 | 23 | 45 | 00 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 38 | 30 43 | 30 31 | 30 38 | 30 35 | 31 30 | 32 33 | 34 35 | 30 30 |  | 0d 0a |

#### ARM Open/Close
- **Example:** Open User 24 Area 2 23:45 10:5:2008

| Field | Start | Address | Length | Command | Event E/R | ID | Area | Yr | Mth | Day | Hr | Min | Sec | Ck | Cr-LF |
|-------|-------|---------|--------|---------|-----------|----|----- |----|-----|-----|----|----- |-----|----|----- |
| **HEX** | 87 | 02 | 03 | 61 | 00 | 18=24 | 02 | 08 | 05 | 10 | 23 | 45 | 00 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 36 31 | 30 38 | 30 43 | 30 31 | 30 38 | 30 35 | 31 30 | 32 33 | 34 35 | 30 30 |  | 0d 0a |

### Legend:

| NESS ID | Main unit 0<br>USER or ZONE identifier 0x01 to 0xfe |
|---------|---------------------------------------------------|
| User | USER ID 1-58 |
| Zone | ZONE ID 1-32 |
| NESS Area | Area unknown 0, area identifier 0x01 to 0x7f |
| AI | AREA 1 = 1, AREA 2 = 2, HOME = 3, DAY = 4 |
| E | EVENT (always even number) |
| R | RESTORE = EVENT+1 (always odd number) |
| DOOR | DOOR ID 1-3 |
| T | TIME mm – MINUTE 00-59 , hh – HOUR 00 to 23 (24hr) |
| D | DATE dd - DAY OF MONTH 01-31, mm – MONTH 1-12,<br>yy – YEAR 00-99 |

### ACCESS CONTROL

#### Door Access
- **Example:** User 40 Door 3 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 30 | 28=40 | 03 | 06 | 10 | 12 | 01 | 06 | ED | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 33 30 | 32 38 | 30 33 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 | 45 44 | 0d 0a |

#### Door Open Too Long
- **Example:** Door 1 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 02 | 01 | 85 | 06 | 10 | 12 | 01 | 06 | C0 | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 32 | 30 31 | 38 35 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 | 43 30 | 0d 0a |

### Legend:

| NESS ID | 0 is main unit<br>0x01 to 0xfe is the USER or ZONE identifier |
|---------|----------------------------------------------------------------|
| User | USER ID 1-58 |
| Zone | ZONE ID 1-32 |
| NESS Area | 0 is unknown area 0x01 to 0x7f is the area identifier |
| AI | AREA ID AREA 1 = 1, AREA 2 = 2, HOME = 3, DAY = 4 |
| E | EVENT (always even number) |
| R | RESTORE = EVENT+1 (always odd number) |
| DOOR | DOOR ID 1-3 |
| T | TIME mm - MINUTE , hh – HOUR(24hr) |
| D | DATE dd - DAY OF MONTH, mm - MONTH, yy - YEAR |

### WARNING

#### Installer Program Mode Restore
- **Example:** 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 01 | 00 | 00 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 31 | 30 30 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Power UP Restore
- **Example:** 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 11 | 00 | 00 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 31 31 | 30 30 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Power Panel Battery
- **Example:** 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 12 | 00 | 00 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 31 32 | 30 30 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Power Mains
- **Example:** 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 10 | 00 | 00 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 31 30 | 30 30 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Radio Key Battery
- **Example:** User 2 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 12 | 02 | 92 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 31 32 | 30 32 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Radio Detector Battery
- **Example:** Zone 9 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 12 | 09 | 91 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 31 32 | 30 39 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Zone Supervisor
- **Example:** Zone 9 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 32 | 09 | 00 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 31 36 | 30 39 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### RTC Adjust
- **Example:** Zone 9 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 18 | 00 | 00 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 31 38 | 30 30 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Exclude Zone Manual
- **Example:** Zone 9 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 04 | 09 | 00 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 34 | 30 39 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Exclude Zone Auto
- **Example:** Zone 9 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 06 | 09 | 00 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 36 | 30 39 | 30 30 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Entry Delay
- **Example:** Zone 1 Area 1 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area | Hours | Mins | Day | Month | Year | Check sum | Cr-LF |
|-------|-------|---------|-----------|---------|-----------|-------|------|-----|-------|------|-----------|-------|
| **HEX** | 87 | 02 | 02 | 01 | 01 | 06 | 10 | 12 | 01 | 06 |  | 0d 0a |
| **ASCII** | 38 37 | 30 32 | 30 32 | 30 31 | 30 31 | 30 36 | 31 30 | 31 32 | 30 31 | 30 36 |  | 0d 0a |

#### Zone SEAL
- **Example:** Zone 32 06:10 12:1:2006

| Field | Start | Address | Event E/R | NESS ID | NESS Area |
|-------|-------|---------|-----------|---------|-----------|
| **HEX** | 83 | 02 | 00 | 10=32d | 00 |
| **ASCII** | 38 33 | 30 32 | 30 30 | 31 30 | 30 30 |

**Note:** 14 byte message

### Legend:

| NESS ID | 0 is main unit<br>0x01 to 0xfe is the USER or ZONE identifier |
|---------|----------------------------------------------------------------|
| User | USER ID 1-58 |
| Zone | ZONE ID 1-32 |
| NESS Area | 0 is unknown area 0x01 to 0x7f is the area identifier |
| AI | AREA ID AREA 1 = 1, AREA 2 = 2, HOME = 3, DAY = 4 |
| E | EVENT (always even number) |
| R | RESTORE = EVENT+1 (always odd number) |
| DOOR | DOOR ID 1-3 |
| T | TIME mm - MINUTE , hh – HOUR(24hr) |
| D | DATE dd - DAY OF MONTH, mm - MONTH, yy - YEAR |

### KEYPAD INPUT Example: Control of AUX 1 TO Aux 4.

The keypad commands 11*, 22*, 33*, 44* will turn ON AUX 1 to AUX 4 respectively.
The keypad commands 11#, 22#, 33#, 44# will turn OFF AUX 1 to AUX 4 respectively.
Note that the corresponding Program option P141E 4E to P144E 4E must be enabled.

### VERSION examples.

1. **8200036017000004**  
   0000 Prior to V7.8

2. **820003601700788c**  
   0078  
   00 = D8x  
   78 = Version 7.8

3. **8200036017008084**  
   0080  
   00 = D8x  
   80 = Version 8.0

4. **820003601714a848** .  
   14a8  
   14 = D16xcel 3G (04 = D8xCel 3G)  
   a8 =Version 10.8 (a = 10)

5. **820003601700877d**  
   00 = D8x (D16x is 10)  
   87 = Version 8.7 ie current product.

6. **820003601715b048** .  
   15b0  
   15 = D16xcel 4G (05 = D8xCel 4G)  
   b0 =Version 11.0 (b = 11)

---

## APPENDIX A.

The format described above for the D32X ASCII Serial Interface is based on the NESSBus specification document.

Changes made to this document that do not conform to the NESSBus specification should be noted. See below for current list.

The table below is copied from the NESSBus specification document.
It lists the CMD_SYSTEM_STATUS (0x61) command bytes.
The D32X does not connect to the NESSBus, however it does conform to the NESSBus specification except as noted in Appendix B.

### NESSBus Specification Reference

#### Event Codes

**Zone/User States**
- 0x00 unsealed
- 0x01 sealed  
- 0x02 alarm
- 0x03 alarm restore
- 0x04 manual exclude
- 0x05 manual include
- 0x06 auto exclude
- 0x07 auto include
- 0x08 tamper unsealed
- 0x09 tamper normal

**System States**
- 0x10 power failure
- 0x11 power normal
- 0x12 battery failure
- 0x13 battery normal
- 0x14 report failure
- 0x15 report normal
- 0x16 supervision failure
- 0x17 supervision normal
- 0x19 real time clock

**Area States**
- 0x20 entry delay started
- 0x21 entry delay ended
- 0x22 exit delay started
- 0x23 exit delay ended
- 0x24 armed away
- 0x25 armed home
- 0x26 armed day
- 0x27 armed night
- 0x28 armed vacation
- 0x2e armed highest
- 0x2f disarmed
- 0x30 arming delayed
- 0x31 status state

**Result States**
- 0x32 Output On
- 0x31 Output Off
- 0xff is reserved

#### Identity Codes

- 0x00 main unit
- 0x01-0xef addition identities such as zone/user number
- 0xf0-0xfe keypads
- 0xff is reserved

#### Area Codes

- 0x00 unknown area
- 0x01 - 0x7f area the event is part of

**Special Area Codes:**
- 0x80 24 hrs
- 0x81 Fire
- 0x82 Panic
- 0x83 Medical
- 0x84 Duress
- 0x85 Door/Doorbell
- 0x90 Radio Device
- 0x91 Radio Detector
- 0x92 Radio Pendant
- 0xa1 Access (Door 1)
- 0xa2 Access (Door 2)
- 0xa3 Access (Door 3)
- 0xa4 Access (Door 4)
- 0xa5 Access (Door 5)
- 0xa6 Access (Door 6)
- 0xb0 Program area
- 0x85-0x8f ??? future
- 0x93-0x9f ??? future
- 0x96-0xfe ??? future
- 0xff is reserved

---

## Appendix B

The following do not conform to the NESSBus specification:

### 1. Output Event Data and the need for *CMD_REQUEST_EVENT*.

**On the NESSBUS:**
*This command is in response to the CMD_REQUEST_EVENT.*
The message is reported so that the entire system is aware of the states of the various devices. Any device can listen to other device's system status if they wish. The CMD_SYSTEM_STATUS is followed by 3 bytes. These 3 bytes represent a specific event as described in the table.

**On the D32X:**
The CMD_REQUEST_EVENT is generated internally.

### 2. Output Event Data Address.

**On the NESSBUS:**
0x00 Address of master.
0x01–0xff Address of slave.

**On the D32X:**
0x00-0xff The D32X identity.

---

**UNCONTROLLED COPY IF PRINTED**  
**Doc ID. D8-32X SERIAL PROTOCOL.DOC**