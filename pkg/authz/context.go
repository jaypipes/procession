package authz

import (
    pb "github.com/jaypipes/procession/proto"
)

type Context struct {
    session *pb.Session
    expiresOn uint64  // UTC microsecond timestamp
    permissions *pb.Permissions
}

func ContextFromSession(sess *pb.Session) (*Context, error) {
    ctx := &Context{
        session: sess,
    }
    return ctx, nil
}
