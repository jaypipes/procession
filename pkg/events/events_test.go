package events

import (
    "io/ioutil"
    "os"
    "testing"

    "github.com/golang/protobuf/proto"
    "github.com/stretchr/testify/assert"

    pb "github.com/jaypipes/procession/proto"
)

func TestEvents(t *testing.T) {
    assert := assert.New(t)
    tmpLogFile, err := ioutil.TempFile("", "archive.log-")
    assert.NoError(err)

    tmpLogPath := tmpLogFile.Name()
    defer os.Remove(tmpLogPath)

    cfg := &Config{
        LogFilePath: tmpLogPath,
    }
    events, err := New(cfg)
    assert.NoError(err)

    trw := &events.Stats.TotalEventsWritten
    tbw := &events.Stats.TotalBytesWritten
    tc := &events.Stats.TotalCreate
    tm := &events.Stats.TotalModify
    td := &events.Stats.TotalDelete

    assert.EqualValues(0, *trw)
    assert.EqualValues(0, *tbw)
    assert.EqualValues(0, *tc)
    assert.EqualValues(0, *tm)
    assert.EqualValues(0, *td)

    sess := &pb.Session{
        User: "actor1",
    }
    etype := pb.EventType_CREATE
    otype := pb.ObjectType_ORGANIZATION
    ouuid := "org1"
    dn := "my org"
    slug := "my-org"

    beforeOrg := &pb.Organization{
        Uuid: ouuid,
        DisplayName: dn,
        Slug: slug,
        Generation: 1,
    }
    beforeb, err := proto.Marshal(beforeOrg)
    assert.NoError(err)

    err = events.Write(sess, etype, otype, ouuid, beforeb, nil)
    assert.NoError(err)

    assert.EqualValues(1, *trw)
    assert.True(0 < *tbw)
    assert.EqualValues(1, *tc)
    assert.EqualValues(0, *tm)
    assert.EqualValues(0, *td)

    ev := &pb.Event{}
    data, err := ioutil.ReadFile(tmpLogPath)
    assert.NoError(err)
    err = proto.Unmarshal(data, ev)
    assert.NoError(err)

    expect := &pb.Event{
        Type: etype,
        ObjectType: otype,
        ObjectUuid: ouuid,
        ActorUuid: sess.User,
        Before: beforeb,
        After: nil,
    }

    assert.Equal(expect.Type, ev.Type)
    assert.Equal(expect.ObjectType, ev.ObjectType)
    assert.Equal(expect.ObjectUuid, ev.ObjectUuid)
    assert.Equal(expect.ActorUuid, ev.ActorUuid)
    assert.Equal(expect.Before, ev.Before)
    assert.Equal(expect.After, ev.After)

    // Test the MODIFY event type and the USER object type
    etype = pb.EventType_MODIFY
    otype = pb.ObjectType_USER
    ouuid = "user1"
    dn = "my user"
    slug = "my-user"
    email := "my@user.org"

    beforeUser := &pb.User{
        Uuid: ouuid,
        DisplayName: dn,
        Slug: slug,
        Email: email,
        Generation: 1,
    }
    beforeb, err = proto.Marshal(beforeUser)
    assert.NoError(err)

    afterUser := &pb.User{
        Uuid: ouuid,
        DisplayName: dn,
        Slug: slug,
        Email: "myother@user.org",
        Generation: 2,
    }
    afterb, err := proto.Marshal(afterUser)
    assert.NoError(err)

    err = events.Write(sess, etype, otype, ouuid, beforeb, afterb)
    assert.NoError(err)

    assert.EqualValues(2, *trw)
    assert.True(0 < *tbw)
    assert.EqualValues(1, *tc)
    assert.EqualValues(1, *tm)
    assert.EqualValues(0, *td)

    // Test the DELETE event type
    etype = pb.EventType_DELETE

    beforeb, err = proto.Marshal(beforeUser)
    assert.NoError(err)

    err = events.Write(sess, etype, otype, ouuid, beforeb, nil)
    assert.NoError(err)

    assert.EqualValues(3, *trw)
    assert.True(0 < *tbw)
    assert.EqualValues(1, *tc)
    assert.EqualValues(1, *tm)
    assert.EqualValues(1, *td)
}
