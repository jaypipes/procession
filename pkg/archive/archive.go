package archive

import (
    "bufio"
    "io"
    "os"
    "time"

    "github.com/golang/protobuf/proto"
    pb "github.com/jaypipes/procession/proto"
)

type Config struct {
    LogFilePath string
    SyncAfterSeconds int
}

type Stats struct {
    TotalRecordsWritten uint64
    TotalBytesWritten uint64
    TotalCreate uint64
    TotalModify uint64
    TotalDelete uint64
}

type Archiver struct {
    wr io.Writer
    start time.Time
    stats *Stats
}

func New(cfg *Config) (*Archiver, error) {
    a := &Archiver{
        start: time.Now().UTC(),
        stats: &Stats{},
    }

    var f *os.File
    f, err := os.OpenFile(cfg.LogFilePath, os.O_APPEND, 0644)
    if err != nil {
        if os.IsNotExist(err) {
            // Archive log file doesn't exist. Try to create it.
            f, err = os.Create(cfg.LogFilePath)
            if err != nil {
                return nil, err
            }
        } else if os.IsPermission(err) {
            // Can't open the file for writing... nothing we can do but exit
            return nil, err
        } else {
            return nil, err
        }
    }
    a.wr = bufio.NewWriter(f)

    return a, nil
}

func (a *Archiver) Archive(rec *pb.ArchiveRecord) error {
    b, err := proto.Marshal(rec)
    if err != nil {
        return err
    }

    written, err := a.wr.Write(b)

    if err != nil {
        return err
    }

    st := a.stats
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
