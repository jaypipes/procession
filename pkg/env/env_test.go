package env

import (
    "os"
    "testing"

    "github.com/stretchr/testify/assert"
)

var (
    key = "TESTING"
)

func TestEnvOrDefaultStr(t *testing.T) {
    assert := assert.New(t)
    val := "value"
    defval := "default"
    os.Setenv(key, val)

    defer os.Unsetenv(key)

    res := EnvOrDefaultStr(key, defval)

    assert.Equal(val, res)

    os.Unsetenv(key)

    res = EnvOrDefaultStr(key, defval)

    assert.Equal(defval, res)
}

func TestEnvOrDefaultInt(t *testing.T) {
    assert := assert.New(t)
    val := "42"
    badval := "meaning of life"
    intval := 42
    defval := 84
    os.Setenv(key, val)

    defer os.Unsetenv(key)

    res := EnvOrDefaultInt(key, defval)

    assert.Equal(intval, res)

    os.Unsetenv(key)

    res = EnvOrDefaultInt(key, defval)

    assert.Equal(defval, res)

    // Verify type conversion failure produces default value
    os.Setenv(key, badval)

    res = EnvOrDefaultInt(key, defval)

    assert.Equal(defval, res)
}

func TestEnvOrDefaultBool(t *testing.T) {
    assert := assert.New(t)
    val := "true"
    badval := "meaning of life"
    boolval := true
    defval := false
    os.Setenv(key, val)

    defer os.Unsetenv(key)

    res := EnvOrDefaultBool(key, defval)

    assert.Equal(boolval, res)

    os.Unsetenv(key)

    res = EnvOrDefaultBool(key, defval)

    assert.Equal(defval, res)

    // Verify type conversion failure produces default value
    os.Setenv(key, badval)

    res = EnvOrDefaultBool(key, defval)

    assert.Equal(defval, res)
}
