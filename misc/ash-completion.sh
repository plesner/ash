#!/bin/sh

_ash_complete() {
  COMPREPLY=( $( $1 --complete-- $2 2>/dev/null ) )
}

complete -F _ash_complete a
