import pytest
from ape import accounts, project
import base64

@pytest.fixture
def base64_encoder():
    return project.Base64Encode.deploy(sender=accounts.test_accounts[0])

def test_encode_empty(base64_encoder):
    """Test encoding an empty array"""
    encoded = base64_encoder.encode([])
    # An empty array should encode to an empty string
    assert ''.join(encoded) == ""

def test_encode_single_byte(base64_encoder):
    """Test encoding a single byte"""
    # Test with 'A' (ASCII 65)
    input_data = [65]
    encoded = base64_encoder.encode(input_data)
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    assert ''.join(encoded) == expected

def test_encode_two_bytes(base64_encoder):
    """Test encoding two bytes"""
    # Test with 'BC' (ASCII 66, 67)
    input_data = [66, 67]
    encoded = base64_encoder.encode(input_data)
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    assert ''.join(encoded) == expected

def test_encode_three_bytes(base64_encoder):
    """Test encoding three bytes exactly (no padding needed)"""
    # Test with 'abc' (ASCII 97, 98, 99)
    input_data = [97, 98, 99]
    encoded = base64_encoder.encode(input_data)
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    assert ''.join(encoded) == expected

def test_encode_four_bytes(base64_encoder):
    """Test encoding four bytes (spanning to a new block)"""
    # Test with 'test' (ASCII 116, 101, 115, 116)
    input_data = [116, 101, 115, 116]
    encoded = base64_encoder.encode(input_data)
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    assert ''.join(encoded) == expected

def test_encode_padding_one(base64_encoder):
    """Test encoding with one padding character"""
    # 'aa' will be encoded as 'YWE=' (1 padding character)
    input_data = [97, 97]
    encoded = base64_encoder.encode(input_data)
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    assert ''.join(encoded) == expected

def test_encode_padding_two(base64_encoder):
    """Test encoding with two padding characters"""
    # 'a' will be encoded as 'YQ==' (2 padding characters)
    input_data = [97]
    encoded = base64_encoder.encode(input_data)
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    assert ''.join(encoded) == expected

def test_encode_hello_world(base64_encoder):
    """Test encoding 'Hello, World!'"""
    input_data = [72, 101, 108, 108, 111, 44, 32, 87, 111, 114, 108, 100, 33]  # "Hello, World!"
    encoded = base64_encoder.encode(input_data)
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    assert ''.join(encoded) == expected

def test_encode_binary_data(base64_encoder):
    """Test encoding binary data with all possible byte values"""
    # Create an array with all byte values from 0 to 255
    input_data = list(range(256))
    encoded = base64_encoder.encode(input_data)
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    assert ''.join(encoded) == expected

def test_encode_large_data(base64_encoder):
    """Test encoding a large amount of data"""
    # 200 bytes of repeating pattern
    input_data = [(i % 256) for i in range(200)]
    encoded = base64_encoder.encode(input_data)
    expected = base64.b64encode(bytes(input_data)).decode('utf-8')
    assert ''.join(encoded) == expected 