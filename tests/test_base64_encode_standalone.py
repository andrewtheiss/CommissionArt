import base64

# This is a Python implementation of the Base64Encode.vy contract's algorithm
def vyper_base64_encode(data):
    """Python implementation of the Vyper contract's base64 encoding function"""
    # Define the Base64 table
    BASE64_TABLE = [
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P",
        "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f",
        "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v",
        "w", "x", "y", "z", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "+", "/"
    ]
    PAD = "="
    
    result_chars = []
    num_iterations = (len(data) + 2) // 3
    
    for j in range(num_iterations):
        i = j * 3
        # Get up to 3 bytes, default to 0 if not present
        b0 = data[i] if i < len(data) else 0
        b1 = data[i + 1] if i + 1 < len(data) else 0
        b2 = data[i + 2] if i + 2 < len(data) else 0
        
        # Calculate the 4 base64 indices
        char0 = (b0 >> 2) & 0x3F
        char1 = ((b0 & 0x03) << 4) | ((b1 >> 4) & 0x0F)
        char2 = ((b1 & 0x0F) << 2) | ((b2 >> 6) & 0x03)
        char3 = b2 & 0x3F
        
        # Map to base64 characters, handling padding
        c0 = BASE64_TABLE[char0]
        c1 = BASE64_TABLE[char1]
        c2 = BASE64_TABLE[char2] if i + 1 < len(data) else PAD
        c3 = BASE64_TABLE[char3] if i + 2 < len(data) else PAD
        
        result_chars.extend([c0, c1, c2, c3])
    
    return ''.join(result_chars)

def test_encoding(input_data, description):
    """Test the encoding with both our implementation and Python's standard base64"""
    # Using our Python implementation of the Vyper contract
    our_result = vyper_base64_encode(input_data)
    
    # Using standard Python base64 library
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    
    # Compare results
    if our_result == expected:
        print(f"✅ {description}: PASSED")
        print(f"   Input: {input_data}")
        print(f"   Output: {our_result}")
    else:
        print(f"❌ {description}: FAILED")
        print(f"   Input: {input_data}")
        print(f"   Our result: {our_result}")
        print(f"   Expected: {expected}")
    
    return our_result == expected

def run_tests():
    """Run all test cases"""
    print("Running Base64 encoding tests...\n")
    
    all_passed = True
    
    # Test case 1: Empty array
    test_result = test_encoding([], "Empty array")
    all_passed = all_passed and test_result
    print()
    
    # Test case 2: Single byte
    test_result = test_encoding([65], "Single byte ('A')")
    all_passed = all_passed and test_result
    print()
    
    # Test case 3: Two bytes
    test_result = test_encoding([66, 67], "Two bytes ('BC')")
    all_passed = all_passed and test_result
    print()
    
    # Test case 4: Three bytes (no padding)
    test_result = test_encoding([97, 98, 99], "Three bytes ('abc')")
    all_passed = all_passed and test_result
    print()
    
    # Test case 5: Four bytes
    test_result = test_encoding([116, 101, 115, 116], "Four bytes ('test')")
    all_passed = all_passed and test_result
    print()
    
    # Test case 6: One padding character
    test_result = test_encoding([97, 97], "One padding character ('aa')")
    all_passed = all_passed and test_result
    print()
    
    # Test case 7: Two padding characters
    test_result = test_encoding([97], "Two padding characters ('a')")
    all_passed = all_passed and test_result
    print()
    
    # Test case 8: Hello World
    hello_world = [72, 101, 108, 108, 111, 44, 32, 87, 111, 114, 108, 100, 33]
    test_result = test_encoding(hello_world, "Hello, World!")
    all_passed = all_passed and test_result
    print()
    
    # Test case 9: Binary data (all byte values)
    binary_data = list(range(256))
    test_result = test_encoding(binary_data, "All byte values (0-255)")
    all_passed = all_passed and test_result
    print()
    
    # Test case 10: Large data
    large_data = [(i % 256) for i in range(200)]
    test_result = test_encoding(large_data, "Large data (200 bytes)")
    all_passed = all_passed and test_result
    print()
    
    # Print overall result
    if all_passed:
        print("🎉 ALL TESTS PASSED! The Base64Encode algorithm works correctly.")
    else:
        print("❌ SOME TESTS FAILED. The algorithm needs correction.")

if __name__ == "__main__":
    run_tests() 