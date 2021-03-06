package events

import (
	"os"
	"time"

	"github.com/golang/protobuf/proto"
	pb "github.com/jaypipes/procession/proto"
)

type Config struct {
	LogFilePath string
}

type Stats struct {
	TotalEventsWritten uint64
	TotalBytesWritten  uint64
	TotalCreate        uint64
	TotalModify        uint64
	TotalDelete        uint64
}

type Events struct {
	f     *os.File
	start time.Time
	Stats *Stats
}

func New(cfg *Config) (*Events, error) {
	e := &Events{
		start: time.Now().UTC(),
		Stats: &Stats{},
	}

	var f *os.File
	f, err := os.Create(cfg.LogFilePath)
	if err != nil {
		return nil, err
	}
	e.f = f

	return e, nil
}

// Memorializes an event, a target (object) and a before and after image of the
// object
func (e *Events) Write(
	sess *pb.Session,
	etype pb.EventType,
	otype pb.ObjectType,
	ouuid string,
	before []byte,
	after []byte,
) error {
	if e == nil {
		return nil
	}
	now := time.Now().UTC()
	ev := &pb.Event{
		Type:       etype,
		ObjectType: otype,
		ObjectUuid: ouuid,
		Timestamp:  now.UnixNano(),
		ActorUuid:  sess.User,
		Before:     before,
		After:      after,
	}
	b, err := proto.Marshal(ev)
	if err != nil {
		return err
	}

	written, err := e.f.Write(b)
	if err != nil {
		return err
	}

	st := e.Stats
	st.TotalEventsWritten++
	st.TotalBytesWritten += uint64(written)
	switch etype {
	case pb.EventType_CREATE:
		st.TotalCreate++
	case pb.EventType_MODIFY:
		st.TotalModify++
	case pb.EventType_DELETE:
		st.TotalDelete++
	}
	return nil
}
