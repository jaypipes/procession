// Code generated by protoc-gen-go.
// source: service_iam.proto
// DO NOT EDIT!

package procession

import proto "github.com/golang/protobuf/proto"
import fmt "fmt"
import math "math"

import (
	context "golang.org/x/net/context"
	grpc "google.golang.org/grpc"
)

// Reference imports to suppress errors if they are not otherwise used.
var _ = proto.Marshal
var _ = fmt.Errorf
var _ = math.Inf

// Reference imports to suppress errors if they are not otherwise used.
var _ context.Context
var _ grpc.ClientConn

// This is a compile-time assertion to ensure that this generated file
// is compatible with the grpc package it is being compiled against.
const _ = grpc.SupportPackageIsVersion4

// Client API for IAM service

type IAMClient interface {
	// Returns information about a specific user
	UserGet(ctx context.Context, in *UserGetRequest, opts ...grpc.CallOption) (*User, error)
	// Deletes a specified user
	UserDelete(ctx context.Context, in *UserDeleteRequest, opts ...grpc.CallOption) (*UserDeleteResponse, error)
	// Set information about a specific user
	UserSet(ctx context.Context, in *UserSetRequest, opts ...grpc.CallOption) (*UserSetResponse, error)
	// Returns information about multiple users
	UserList(ctx context.Context, in *UserListRequest, opts ...grpc.CallOption) (IAM_UserListClient, error)
	// List users belonging to a user
	UserMembersList(ctx context.Context, in *UserMembersListRequest, opts ...grpc.CallOption) (IAM_UserMembersListClient, error)
	// Returns information about a specific organization
	OrganizationGet(ctx context.Context, in *OrganizationGetRequest, opts ...grpc.CallOption) (*Organization, error)
	// Deletes a specified organization
	OrganizationDelete(ctx context.Context, in *OrganizationDeleteRequest, opts ...grpc.CallOption) (*OrganizationDeleteResponse, error)
	// Set information about a specific organization
	OrganizationSet(ctx context.Context, in *OrganizationSetRequest, opts ...grpc.CallOption) (*OrganizationSetResponse, error)
	// Returns information about multiple organizations
	OrganizationList(ctx context.Context, in *OrganizationListRequest, opts ...grpc.CallOption) (IAM_OrganizationListClient, error)
	// Add or remove users from an organization
	OrganizationMembersSet(ctx context.Context, in *OrganizationMembersSetRequest, opts ...grpc.CallOption) (*OrganizationMembersSetResponse, error)
	// List users belonging to an organization
	OrganizationMembersList(ctx context.Context, in *OrganizationMembersListRequest, opts ...grpc.CallOption) (IAM_OrganizationMembersListClient, error)
}

type iAMClient struct {
	cc *grpc.ClientConn
}

func NewIAMClient(cc *grpc.ClientConn) IAMClient {
	return &iAMClient{cc}
}

func (c *iAMClient) UserGet(ctx context.Context, in *UserGetRequest, opts ...grpc.CallOption) (*User, error) {
	out := new(User)
	err := grpc.Invoke(ctx, "/procession.IAM/user_get", in, out, c.cc, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *iAMClient) UserDelete(ctx context.Context, in *UserDeleteRequest, opts ...grpc.CallOption) (*UserDeleteResponse, error) {
	out := new(UserDeleteResponse)
	err := grpc.Invoke(ctx, "/procession.IAM/user_delete", in, out, c.cc, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *iAMClient) UserSet(ctx context.Context, in *UserSetRequest, opts ...grpc.CallOption) (*UserSetResponse, error) {
	out := new(UserSetResponse)
	err := grpc.Invoke(ctx, "/procession.IAM/user_set", in, out, c.cc, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *iAMClient) UserList(ctx context.Context, in *UserListRequest, opts ...grpc.CallOption) (IAM_UserListClient, error) {
	stream, err := grpc.NewClientStream(ctx, &_IAM_serviceDesc.Streams[0], c.cc, "/procession.IAM/user_list", opts...)
	if err != nil {
		return nil, err
	}
	x := &iAMUserListClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type IAM_UserListClient interface {
	Recv() (*User, error)
	grpc.ClientStream
}

type iAMUserListClient struct {
	grpc.ClientStream
}

func (x *iAMUserListClient) Recv() (*User, error) {
	m := new(User)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (c *iAMClient) UserMembersList(ctx context.Context, in *UserMembersListRequest, opts ...grpc.CallOption) (IAM_UserMembersListClient, error) {
	stream, err := grpc.NewClientStream(ctx, &_IAM_serviceDesc.Streams[1], c.cc, "/procession.IAM/user_members_list", opts...)
	if err != nil {
		return nil, err
	}
	x := &iAMUserMembersListClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type IAM_UserMembersListClient interface {
	Recv() (*Organization, error)
	grpc.ClientStream
}

type iAMUserMembersListClient struct {
	grpc.ClientStream
}

func (x *iAMUserMembersListClient) Recv() (*Organization, error) {
	m := new(Organization)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (c *iAMClient) OrganizationGet(ctx context.Context, in *OrganizationGetRequest, opts ...grpc.CallOption) (*Organization, error) {
	out := new(Organization)
	err := grpc.Invoke(ctx, "/procession.IAM/organization_get", in, out, c.cc, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *iAMClient) OrganizationDelete(ctx context.Context, in *OrganizationDeleteRequest, opts ...grpc.CallOption) (*OrganizationDeleteResponse, error) {
	out := new(OrganizationDeleteResponse)
	err := grpc.Invoke(ctx, "/procession.IAM/organization_delete", in, out, c.cc, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *iAMClient) OrganizationSet(ctx context.Context, in *OrganizationSetRequest, opts ...grpc.CallOption) (*OrganizationSetResponse, error) {
	out := new(OrganizationSetResponse)
	err := grpc.Invoke(ctx, "/procession.IAM/organization_set", in, out, c.cc, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *iAMClient) OrganizationList(ctx context.Context, in *OrganizationListRequest, opts ...grpc.CallOption) (IAM_OrganizationListClient, error) {
	stream, err := grpc.NewClientStream(ctx, &_IAM_serviceDesc.Streams[2], c.cc, "/procession.IAM/organization_list", opts...)
	if err != nil {
		return nil, err
	}
	x := &iAMOrganizationListClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type IAM_OrganizationListClient interface {
	Recv() (*Organization, error)
	grpc.ClientStream
}

type iAMOrganizationListClient struct {
	grpc.ClientStream
}

func (x *iAMOrganizationListClient) Recv() (*Organization, error) {
	m := new(Organization)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (c *iAMClient) OrganizationMembersSet(ctx context.Context, in *OrganizationMembersSetRequest, opts ...grpc.CallOption) (*OrganizationMembersSetResponse, error) {
	out := new(OrganizationMembersSetResponse)
	err := grpc.Invoke(ctx, "/procession.IAM/organization_members_set", in, out, c.cc, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *iAMClient) OrganizationMembersList(ctx context.Context, in *OrganizationMembersListRequest, opts ...grpc.CallOption) (IAM_OrganizationMembersListClient, error) {
	stream, err := grpc.NewClientStream(ctx, &_IAM_serviceDesc.Streams[3], c.cc, "/procession.IAM/organization_members_list", opts...)
	if err != nil {
		return nil, err
	}
	x := &iAMOrganizationMembersListClient{stream}
	if err := x.ClientStream.SendMsg(in); err != nil {
		return nil, err
	}
	if err := x.ClientStream.CloseSend(); err != nil {
		return nil, err
	}
	return x, nil
}

type IAM_OrganizationMembersListClient interface {
	Recv() (*User, error)
	grpc.ClientStream
}

type iAMOrganizationMembersListClient struct {
	grpc.ClientStream
}

func (x *iAMOrganizationMembersListClient) Recv() (*User, error) {
	m := new(User)
	if err := x.ClientStream.RecvMsg(m); err != nil {
		return nil, err
	}
	return m, nil
}

// Server API for IAM service

type IAMServer interface {
	// Returns information about a specific user
	UserGet(context.Context, *UserGetRequest) (*User, error)
	// Deletes a specified user
	UserDelete(context.Context, *UserDeleteRequest) (*UserDeleteResponse, error)
	// Set information about a specific user
	UserSet(context.Context, *UserSetRequest) (*UserSetResponse, error)
	// Returns information about multiple users
	UserList(*UserListRequest, IAM_UserListServer) error
	// List users belonging to a user
	UserMembersList(*UserMembersListRequest, IAM_UserMembersListServer) error
	// Returns information about a specific organization
	OrganizationGet(context.Context, *OrganizationGetRequest) (*Organization, error)
	// Deletes a specified organization
	OrganizationDelete(context.Context, *OrganizationDeleteRequest) (*OrganizationDeleteResponse, error)
	// Set information about a specific organization
	OrganizationSet(context.Context, *OrganizationSetRequest) (*OrganizationSetResponse, error)
	// Returns information about multiple organizations
	OrganizationList(*OrganizationListRequest, IAM_OrganizationListServer) error
	// Add or remove users from an organization
	OrganizationMembersSet(context.Context, *OrganizationMembersSetRequest) (*OrganizationMembersSetResponse, error)
	// List users belonging to an organization
	OrganizationMembersList(*OrganizationMembersListRequest, IAM_OrganizationMembersListServer) error
}

func RegisterIAMServer(s *grpc.Server, srv IAMServer) {
	s.RegisterService(&_IAM_serviceDesc, srv)
}

func _IAM_UserGet_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(UserGetRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(IAMServer).UserGet(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/procession.IAM/UserGet",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(IAMServer).UserGet(ctx, req.(*UserGetRequest))
	}
	return interceptor(ctx, in, info, handler)
}

func _IAM_UserDelete_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(UserDeleteRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(IAMServer).UserDelete(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/procession.IAM/UserDelete",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(IAMServer).UserDelete(ctx, req.(*UserDeleteRequest))
	}
	return interceptor(ctx, in, info, handler)
}

func _IAM_UserSet_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(UserSetRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(IAMServer).UserSet(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/procession.IAM/UserSet",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(IAMServer).UserSet(ctx, req.(*UserSetRequest))
	}
	return interceptor(ctx, in, info, handler)
}

func _IAM_UserList_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(UserListRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(IAMServer).UserList(m, &iAMUserListServer{stream})
}

type IAM_UserListServer interface {
	Send(*User) error
	grpc.ServerStream
}

type iAMUserListServer struct {
	grpc.ServerStream
}

func (x *iAMUserListServer) Send(m *User) error {
	return x.ServerStream.SendMsg(m)
}

func _IAM_UserMembersList_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(UserMembersListRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(IAMServer).UserMembersList(m, &iAMUserMembersListServer{stream})
}

type IAM_UserMembersListServer interface {
	Send(*Organization) error
	grpc.ServerStream
}

type iAMUserMembersListServer struct {
	grpc.ServerStream
}

func (x *iAMUserMembersListServer) Send(m *Organization) error {
	return x.ServerStream.SendMsg(m)
}

func _IAM_OrganizationGet_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(OrganizationGetRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(IAMServer).OrganizationGet(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/procession.IAM/OrganizationGet",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(IAMServer).OrganizationGet(ctx, req.(*OrganizationGetRequest))
	}
	return interceptor(ctx, in, info, handler)
}

func _IAM_OrganizationDelete_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(OrganizationDeleteRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(IAMServer).OrganizationDelete(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/procession.IAM/OrganizationDelete",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(IAMServer).OrganizationDelete(ctx, req.(*OrganizationDeleteRequest))
	}
	return interceptor(ctx, in, info, handler)
}

func _IAM_OrganizationSet_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(OrganizationSetRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(IAMServer).OrganizationSet(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/procession.IAM/OrganizationSet",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(IAMServer).OrganizationSet(ctx, req.(*OrganizationSetRequest))
	}
	return interceptor(ctx, in, info, handler)
}

func _IAM_OrganizationList_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(OrganizationListRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(IAMServer).OrganizationList(m, &iAMOrganizationListServer{stream})
}

type IAM_OrganizationListServer interface {
	Send(*Organization) error
	grpc.ServerStream
}

type iAMOrganizationListServer struct {
	grpc.ServerStream
}

func (x *iAMOrganizationListServer) Send(m *Organization) error {
	return x.ServerStream.SendMsg(m)
}

func _IAM_OrganizationMembersSet_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(OrganizationMembersSetRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(IAMServer).OrganizationMembersSet(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/procession.IAM/OrganizationMembersSet",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(IAMServer).OrganizationMembersSet(ctx, req.(*OrganizationMembersSetRequest))
	}
	return interceptor(ctx, in, info, handler)
}

func _IAM_OrganizationMembersList_Handler(srv interface{}, stream grpc.ServerStream) error {
	m := new(OrganizationMembersListRequest)
	if err := stream.RecvMsg(m); err != nil {
		return err
	}
	return srv.(IAMServer).OrganizationMembersList(m, &iAMOrganizationMembersListServer{stream})
}

type IAM_OrganizationMembersListServer interface {
	Send(*User) error
	grpc.ServerStream
}

type iAMOrganizationMembersListServer struct {
	grpc.ServerStream
}

func (x *iAMOrganizationMembersListServer) Send(m *User) error {
	return x.ServerStream.SendMsg(m)
}

var _IAM_serviceDesc = grpc.ServiceDesc{
	ServiceName: "procession.IAM",
	HandlerType: (*IAMServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "user_get",
			Handler:    _IAM_UserGet_Handler,
		},
		{
			MethodName: "user_delete",
			Handler:    _IAM_UserDelete_Handler,
		},
		{
			MethodName: "user_set",
			Handler:    _IAM_UserSet_Handler,
		},
		{
			MethodName: "organization_get",
			Handler:    _IAM_OrganizationGet_Handler,
		},
		{
			MethodName: "organization_delete",
			Handler:    _IAM_OrganizationDelete_Handler,
		},
		{
			MethodName: "organization_set",
			Handler:    _IAM_OrganizationSet_Handler,
		},
		{
			MethodName: "organization_members_set",
			Handler:    _IAM_OrganizationMembersSet_Handler,
		},
	},
	Streams: []grpc.StreamDesc{
		{
			StreamName:    "user_list",
			Handler:       _IAM_UserList_Handler,
			ServerStreams: true,
		},
		{
			StreamName:    "user_members_list",
			Handler:       _IAM_UserMembersList_Handler,
			ServerStreams: true,
		},
		{
			StreamName:    "organization_list",
			Handler:       _IAM_OrganizationList_Handler,
			ServerStreams: true,
		},
		{
			StreamName:    "organization_members_list",
			Handler:       _IAM_OrganizationMembersList_Handler,
			ServerStreams: true,
		},
	},
	Metadata: "service_iam.proto",
}

func init() { proto.RegisterFile("service_iam.proto", fileDescriptor3) }

var fileDescriptor3 = []byte{
	// 322 bytes of a gzipped FileDescriptorProto
	0x1f, 0x8b, 0x08, 0x00, 0x00, 0x09, 0x6e, 0x88, 0x02, 0xff, 0x8c, 0x93, 0xcf, 0x4b, 0xfb, 0x40,
	0x10, 0xc5, 0xfb, 0xe5, 0x0b, 0xfe, 0x18, 0x2f, 0xcd, 0x78, 0xa9, 0x11, 0x3d, 0x44, 0x14, 0xf4,
	0x10, 0x44, 0x6f, 0x1e, 0x04, 0x41, 0x11, 0xc1, 0x2a, 0x54, 0xea, 0x4d, 0x4a, 0x5a, 0xc7, 0xb2,
	0xd0, 0x64, 0xe3, 0xce, 0xd6, 0x83, 0x7f, 0x98, 0x7f, 0x9f, 0x74, 0x93, 0xa6, 0x9b, 0x98, 0x4d,
	0x7a, 0x0b, 0x3b, 0x6f, 0x3e, 0x79, 0xfb, 0x5e, 0x02, 0x1e, 0x93, 0xfa, 0x12, 0x13, 0x1a, 0x89,
	0x28, 0x0e, 0x53, 0x25, 0xb5, 0x44, 0x48, 0x95, 0x9c, 0x10, 0xb3, 0x90, 0x89, 0x8f, 0x52, 0x4d,
	0xa3, 0x44, 0x7c, 0x47, 0x5a, 0xc8, 0x24, 0x9b, 0xfb, 0x30, 0x67, 0x52, 0xd9, 0xf3, 0xc5, 0xcf,
	0x26, 0xfc, 0x7f, 0xb8, 0xe9, 0xe3, 0x15, 0x6c, 0x2d, 0x4e, 0x47, 0x53, 0xd2, 0xe8, 0x87, 0x2b,
	0x40, 0x38, 0x64, 0x52, 0xf7, 0xa4, 0x07, 0xf4, 0x39, 0x27, 0xd6, 0x7e, 0xb7, 0x3a, 0x0b, 0x3a,
	0xf8, 0x04, 0x3b, 0x66, 0xf7, 0x9d, 0x66, 0xa4, 0x09, 0x0f, 0xaa, 0x92, 0x5b, 0x73, 0xbe, 0x24,
	0x1c, 0xba, 0xc6, 0x9c, 0xca, 0x84, 0x29, 0xe8, 0xe0, 0x5d, 0xee, 0x85, 0xeb, 0xbc, 0xbc, 0xac,
	0xbc, 0xec, 0xd7, 0xce, 0x0a, 0xcc, 0x35, 0x6c, 0x1b, 0xcc, 0x4c, 0xb0, 0xc6, 0x3f, 0xda, 0x47,
	0xc1, 0x4d, 0x97, 0x3a, 0xff, 0x87, 0x43, 0xf0, 0xcc, 0x7e, 0x4c, 0xf1, 0x98, 0x14, 0x67, 0x9c,
	0xa0, 0x2a, 0xed, 0x67, 0x53, 0x1b, 0xd7, 0xb3, 0x35, 0xcf, 0x56, 0xfe, 0x06, 0x3b, 0x80, 0xae,
	0xdd, 0x89, 0x49, 0x3c, 0x70, 0x6d, 0x58, 0xc9, 0x37, 0x50, 0xf1, 0x03, 0x76, 0x4b, 0xcc, 0xbc,
	0x89, 0x63, 0xd7, 0x4a, 0xb9, 0x91, 0x93, 0x36, 0x59, 0x11, 0xe9, 0x5b, 0xc5, 0x3b, 0x37, 0x79,
	0xb7, 0x9a, 0x3a, 0x6a, 0xd4, 0x14, 0xf8, 0x57, 0xf0, 0x4a, 0x78, 0x93, 0xb8, 0x73, 0x77, 0xfd,
	0xc8, 0x19, 0x7a, 0x25, 0xee, 0xb2, 0xd1, 0x85, 0xfd, 0x53, 0xd7, 0x66, 0x5e, 0xac, 0x75, 0x8b,
	0xb3, 0x75, 0xa4, 0x56, 0x56, 0x7b, 0xb5, 0x2f, 0x35, 0x97, 0x6a, 0x43, 0xb5, 0x7e, 0x9d, 0xe3,
	0x0d, 0xf3, 0xff, 0x5e, 0xfe, 0x06, 0x00, 0x00, 0xff, 0xff, 0xd3, 0x71, 0xbc, 0xed, 0x00, 0x04,
	0x00, 0x00,
}
