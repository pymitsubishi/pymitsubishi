# Mitsubishi Protocol Research

## Detailed Analysis of CODE Values

This section provides a comprehensive breakdown of the Mitsubishi protocol CODE values used for communication with the MAC-577IF-2E air conditioner.

### Overview

Each CODE value represents a segment of data transmitted between the device and the client. The data is interpreted according to specific rules and transformations to provide meaningful information about the device's state.

### Code Breakdown

#### CODE_0: General States
- **Raw Value:** `fc62013010020000010b190001000085ad28000000db`
- **Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation | Interpretation                    |
  |------------|-----------|-----------|----------------|-----------------------------------|
  | 0-1        | Byte      | `fc`      | -              | Magic Byte                        |
  | 2-3        | Byte      | `62`      | -              | Transfer Mode: read response      |
  | 4-9        | Bytes     | `013010`  | -              | Static bytes                     |
  | 10-11      | Byte      | `02`      | -              | Group Code: General States        |
  | 12-13      | Byte      | `00`      | -              | Unused                            |
  | 14-15      | Enum      | `01`      | -              | Power: ON                         |
  | 16-17      | Enum      | `0b`      | -              | Mode: COOLER                      |
  | 18-19      | Byte      | `19`      | -              | Unknown - i-See detection         |
  | 20-21      | Int       | `00`      | Temp normalization | Temperature: calculated         |
  | 22-23      | Enum      | `01`      | -              | Fan Speed: AUTO                   |
  | 24-25      | Enum      | `00`      | -              | Vertical Wind Dir. (Right): V1    |
  | 26-27      | Enum      | `85`      | -              | Vertical Wind Dir. (Left): AUTO   |
  | 28-29      | Int       | `ad`      | -              | Horizontal Wind Direction: R      |
  | 30-31      | Int       | `28`      | -              | Dehumidification Setting          |
  | 32-33      | Byte      | `00`      | -              | Power Saving Mode: Disabled       |
  | 34-42      | Byte      | `000000`  | -              | Undocumented                      |
  | 43-44      | Byte      | `db`      | -              | Checksum                          |

#### CODE_1: Sensor States
- **Raw Value:** `fc620130100300000b00a0aaaafe420011b96d0000e4`
- **Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation         | Interpretation                   |
  |------------|-----------|-----------|------------------------|----------------------------------|
  | 0-1        | Byte      | `fc`      | -                      | Magic Byte                       |
  | 2-3        | Byte      | `62`      | -                      | Transfer Mode: read response     |
  | 4-9        | Bytes     | `013010`  | -                      | Static bytes                    |
  | 10-11      | Byte      | `03`      | -                      | Group Code: Sensor States        |
  | 12-13      | Byte      | `00`      | -                      | Unused                           |
  | 14-15      | Int       | `0b`      | -                      | Unknown                          |
  | 16-17      | Int       | `00`      | Temp normalization     | Room Temperature: calculated     |
  | 18-19      | Int       | `a0`      | Temp normalization     | Outside Temperature: calculated  |
  | 20-21      | Int       | `aa`      | -                      | Thermal Sensor: false            |
  | 22-23      | Int       | `aa`      | -                      | Wind Speed (PR557): 0            |
  | 24-42      | Byte      | `fe420011b96d0000` | -              | Undocumented                     |
  | 43-44      | Byte      | `e4`      | -                      | Checksum                         |

#### CODE_2: Error States
- **Raw Value:** `fc6201301004000000800000000000000000000000d9`
- **Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation         | Interpretation                   |
  |------------|-----------|-----------|------------------------|----------------------------------|
  | 0-1        | Byte      | `fc`      | -                      | Magic Byte                       |
  | 2-3        | Byte      | `62`      | -                      | Transfer Mode: read response     |
  | 4-9        | Bytes     | `013010`  | -                      | Static bytes                    |
  | 10-11      | Byte      | `04`      | -                      | Group Code: Error States         |
  | 12-21      | Byte      | `00000080`| -                      | Error Code                       |
  | 22-42      | Byte      | `0000000000000000` | -              | Undocumented                     |
  | 43-44      | Byte      | `d9`      | -                      | Checksum                         |

#### CODE_3: Timer Settings
- **Raw Value:** `fc620130100500000000000000000000000000000058`
- **Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation | Interpretation                   |
  |------------|-----------|-----------|----------------|----------------------------------|
  | 0-1        | Byte      | `fc`      | -              | Magic Byte                       |
  | 2-3        | Byte      | `62`      | -              | Transfer Mode: read response     |
  | 4-9        | Bytes     | `013010`  | -              | Static bytes                    |
  | 10-11      | Byte      | `05`      | -              | Group Code: Timer Settings       |
  | 12-42      | Byte      | `000000000000000000000000000000` | - | N/A                            |
  | 43-44      | Byte      | `58`      | -              | Checksum                         |

#### CODE_4: Energy/Status
- **Raw Value:** `fc6201301006000000000004224000004200000000af`
- **Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation | Interpretation                   |
  |------------|-----------|-----------|----------------|----------------------------------|
  | 0-1        | Byte      | `fc`      | -              | Magic Byte                       |
  | 2-3        | Byte      | `62`      | -              | Transfer Mode: read response     |
  | 4-9        | Bytes     | `013010`  | -              | Static bytes                    |
  | 10-11      | Byte      | `06`      | -              | Group Code: Energy/Status        |
  | 12-21      | Byte      | `00000000`| -              | Compressor frequency             |
  | 22-42      | Byte      | `04224000004200000000` | - | Unknown                         |
  | 43-44      | Byte      | `af`      | -              | Checksum                         |

#### CODE_5: Auto Mode Type
- **Raw Value:** `fc620130100900000001000000000000000000000053`
- **Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation | Interpretation                    |
  |------------|-----------|-----------|----------------|-----------------------------------|
  | 0-1        | Byte      | `fc`      | -              | Magic Byte                        |
  | 2-3        | Byte      | `62`      | -              | Transfer Mode: read response      |
  | 4-9        | Bytes     | `013010`  | -              | Static bytes                     |
  | 10-11      | Byte      | `09`      | -              | Group Code: Auto Mode Type        |
  | 12-42      | Byte      | `000000010000000000000000000000` | - | N/A                             |
  | 43-44      | Byte      | `53`      | -              | Checksum                          |


### Notes
- **Temperature Transformation:** Values like room and outside temp are transformed using normalizing functions to interpret the raw hex.
- **Undocumented Areas:** Segments marked as 'Undocumented' have raw data that requires further research.
- **Static and Checksum:** These bytes facilitate communication integrity and setup but are not further analyzed as data.

### Conclusion

This comprehensive documentation outlines how each part of the payload is parsed and used, or not used, providing insight into the detailed protocol handling of the air conditioning system.

# Mitsubishi Protocol Research

## Detailed Analysis of CODE Values

This section provides a comprehensive breakdown of the Mitsubishi protocol CODE values used for communication with the MAC-577IF-2E air conditioner.

### Overview

Each CODE value represents a segment of data transmitted between the device and the client. The data is interpreted according to specific rules and transformations to provide meaningful information about the device's state.

### Detailed Breakdown

#### CODE_0: General States
- **Raw Value:** `fc62013010020000010b190001000085ad28000000db`
- **Detailed Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation | Interpretation                    |
  |------------|-----------|-----------|----------------|-----------------------------------|
  | 0-1        | Byte      | `fc`      | -              | Magic Byte                        |
  | 2-3        | Byte      | `62`      | -              | Transfer Mode: read response      |
  | ...        | ...       | ...       | ...            | ...                               |

#### CODE_1: Sensor States
- **Raw Value:** `fc620130100300000b00a0aaaafe420011b96d0000e4`
- **Detailed Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation         | Interpretation                   |
  |------------|-----------|-----------|------------------------|----------------------------------|
  | 0-1        | Byte      | `fc`      | -                      | Magic Byte                       |
  | 2-3        | Byte      | `62`      | -                      | Transfer Mode: read response     |
  | ...        | ...       | ...       | ...                    | ...                              |

#### CODE_2: Error States
- **Raw Value:** `fc6201301004000000800000000000000000000000d9`
- **Detailed Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation         | Interpretation                   |
  |------------|-----------|-----------|------------------------|----------------------------------|
  | 0-1        | Byte      | `fc`      | -                      | Magic Byte                       |
  | 2-3        | Byte      | `62`      | -                      | Transfer Mode: read response     |
  | ...        | ...       | ...       | ...                    | ...                              |

#### CODE_3: Timer Settings
- **Raw Value:** `fc620130100500000000000000000000000000000058`
- **Detailed Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation | Interpretation                   |
  |------------|-----------|-----------|----------------|----------------------------------|
  | 0-1        | Byte      | `fc`      | -              | Magic Byte                       |
  | 2-3        | Byte      | `62`      | -              | Transfer Mode: read response     |
  | ...        | ...       | ...       | ...            | ...                             |

#### CODE_4: Energy/Status
- **Raw Value:** `fc6201301006000000000004224000004200000000af`
- **Detailed Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation | Interpretation                   |
  |------------|-----------|-----------|----------------|----------------------------------|
  | 0-1        | Byte      | `fc`      | -              | Magic Byte                       |
  | 2-3        | Byte      | `62`      | -              | Transfer Mode: read response     |
  | ...        | ...       | ...       | ...            | ...                             |

#### CODE_5: Auto Mode Type
- **Raw Value:** `fc620130100900000001000000000000000000000053`
- **Detailed Breakdown:**
  | Byte Range | Data Type | Raw Value | Transformation | Interpretation                    |
  |------------|-----------|-----------|----------------|-----------------------------------|
  | 0-1        | Byte      | `fc`      | -              | Magic Byte                        |
  | 2-3        | Byte      | `62`      | -              | Transfer Mode: read response      |
  | ...        | ...       | ...       | ...            | ...                             |

### Notes
- **Temperature Transformation:** Values are transformed using normalizing functions to interpret raw hex.
- **Undocumented Areas:** Segments marked as 'Undocumented' have raw data requiring further research.

### Conclusion

This documentation outlines how each part of the payload is used or not used, providing insight into the detailed protocol handling of the air conditioning system.

