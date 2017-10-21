package util

import (
	"fmt"
	"net"
	"strings"
)

func BindHost() string {
	c, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		fmt.Println("Warning: unable to make a UDP request to 8.8.8.8:80 " +
			"to determine local host address. Using 0.0.0.0")
		return "0.0.0.0"
	}
	defer c.Close()
	addr := c.LocalAddr().String()
	return addr[:strings.LastIndex(addr, ":")]
}
