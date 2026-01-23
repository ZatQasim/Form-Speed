package main

import (
	"fmt"
	"log"
	"net"
	"time"
)

func main() {
	log.Println("[Routing Server] Starting server on port 9000")
	listener, err := net.Listen("tcp", ":9000")
	if err != nil {
		log.Fatal(err)
	}
	defer listener.Close()

	log.Println("[Routing Server] Listening for device connections")

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Println("Connection error:", err)
			continue
		}

		go handleConnection(conn)
	}
}

func handleConnection(conn net.Conn) {
	defer conn.Close()
	buf := make([]byte, 4096)
	n, err := conn.Read(buf)
	if err != nil {
		log.Println("Read error:", err)
		return
	}

	request := string(buf[:n])
	log.Printf("[Routing Server] Received: %s\n", request)

	// Placeholder routing response
	response := fmt.Sprintf(`{"route":"regional-node-1"}`)
	conn.Write([]byte(response))
}