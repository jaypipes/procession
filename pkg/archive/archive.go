package archive

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
    TotalRecordsWritten uint64
    TotalBytesWritten uint64
    TotalCreate uint64
    TotalModify uint64
    TotalDelete uint64
}

type Archiver struct {
    f *os.File
    start time.Time
    Stats *Stats
}

func New(cfg *Config) (*Archiver, error) {
    a := &Archiver{
        start: time.Now().UTC(),
        Stats: &Stats{},
    }

    var f *os.File
    f, err := os.Create(cfg.LogFilePath)
    if err != nil {
        return nil, err
    }
    a.f = f

    return a, nil
}

func (a *Archiver) Archive(rec *pb.ArchiveRecord) error {
    b, err := proto.Marshal(rec)
    if err != nil {
        return err
    }

    written, err := a.f.Write(b)
    if err != nil {
        return err
    }

    st := a.Stats
    st.TotalRecordsWritten++
    st.TotalBytesWritten += uint64(written)
    switch action := rec.Action; action {
    case pb.ArchiveAction_CREATE:
        st.TotalCreate++
    case pb.ArchiveAction_MODIFY:
        st.TotalModify++
    case pb.ArchiveAction_DELETE:
        st.TotalDelete++
    }
    return nil
}
