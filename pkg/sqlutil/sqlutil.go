package sqlutil

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
