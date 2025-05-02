# @version 0.4.1

BASE64_TABLE: constant(DynArray[String[1], 64]) = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P",
    "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f",
    "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v",
    "w", "x", "y", "z", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "+", "/"
]
PAD: constant(String[1]) = "="


@external
def encode(data: DynArray[uint8, 45000]) -> DynArray[String[1],272]:
    result_chars: DynArray[String[1],272] = []
    pos: uint256 = 0
    num_iterations: uint256 = (len(data) + 2) // 3

    for j: uint256 in range(num_iterations, bound=68):
        i: uint256 = j * 3
        # Get up to 3 bytes, default to 0 if not present
        b0: uint8 = 0
        if i < len(data):
            b0 = data[i]
        b1: uint8 = 0
        if i + 1 < len(data):
            b1 = data[i + 1]
        b2: uint8 = 0
        if i + 2 < len(data):
            b2 = data[i + 2]
        
        # Calculate the 4 base64 indices
        char0: uint8 = convert((convert(b0, uint256) >> 2) & convert(0x3F, uint256), uint8)
        char1: uint8 = convert( ( (convert(b0, uint256) & convert(0x03, uint256)) << 4 ) | ( (convert(b1, uint256) >> 4) & convert(0x0F, uint256) ), uint8 )
        char2: uint8 = convert( ( (convert(b1, uint256) & convert(0x0F, uint256)) << 2 ) | ( (convert(b2, uint256) >> 6) & convert(0x03, uint256) ), uint8 )
        char3: uint8 = convert( convert(b2, uint256) & convert(0x3F, uint256), uint8 )
        
        # Map to base64 characters, handling padding
        c0: String[1] = BASE64_TABLE[char0]
        c1: String[1] = BASE64_TABLE[char1]
        c2: String[1] = PAD
        if i + 1 < len(data):
            c2 = BASE64_TABLE[char2]
        c3: String[1] = PAD
        if i + 2 < len(data):
            c3 = BASE64_TABLE[char3]

        # Store in array
        result_chars[pos] = c0
        result_chars[pos + 1] = c1
        result_chars[pos + 2] = c2
        result_chars[pos + 3] = c3
        pos += 4

    # result: Bytes[272] = b""
    # test: Bytes[4] = b"asdf"
    # result = concat(result, test)
    
    return result_chars