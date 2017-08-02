package sqlutil

import (
    "strings"

    "github.com/go-sql-driver/mysql"
)

// Returns a string containing the expression IN with one or more question
// marks for parameter interpolation. If numArgs argument is 3, the returned
// value would be "IN (?, ?, ?)"
func InParamString(numArgs int) string {
    resLen := 5 + ((numArgs * 3) - 2)
    res := make([]byte, resLen)
    res[0] = 'I'
    res[1] = 'N'
    res[2] = ' '
    res[3] = '('
    for x := 4; x < (resLen - 1); x++ {
        res[x] = '?'
        x++
        if x < (resLen - 1) {
            res[x] = ','
            x++
            res[x] = ' '
        }
    }
    res[resLen - 1] = ')'
    return string(res)
}

// Returns true if the supplied error represents a duplicate key error
func IsDuplicateKey(err error) bool {
    if err == nil {
        return false
    }
    me, ok := err.(*mysql.MySQLError)
    if ! ok {
        // TODO(jaypipes): Handle PostgreSQLisms here
        return false
    }
    if me.Number == 1062 {
        return true
    }
    return false
}

// Returns true if the supplied error is a duplicate key error and the supplied
// constraint name is the one that was violated
func IsDuplicateKeyOn(err error, constraintName string) bool {
    if err == nil {
        return false
    }
    me, ok := err.(*mysql.MySQLError)
    if ! ok {
        // TODO(jaypipes): Handle PostgreSQLisms here
        return false
    }
    return strings.Contains(me.Error(), constraintName)
}
